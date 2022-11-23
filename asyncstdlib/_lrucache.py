"""
Reimplementation of ``functools.lru_cache`` as async based on CPython 3.8

This is loosely based on the CPython 3.8 implementation. In specific,
several performance hacks are skipped in favour of maintainability,
especially when they might not apply to PyPy.
"""
from typing import (
    NamedTuple,
    Callable,
    Any,
    Optional,
    Tuple,
    Dict,
    Union,
    Hashable,
    overload,
    cast,
)
from functools import update_wrapper
from collections import OrderedDict

from ._typing import Protocol, TypedDict, AC
from ._utility import public_module


@public_module("asyncstdlib.functools")
class CacheInfo(NamedTuple):
    """
    Metadata on the current state of a cache

    This is a :py:class:`~typing.NamedTuple`, meaning it can be unpacked in assignments.
    The order is ``hits, misses, maxsize, currsize = cache_info``.
    """

    #: Number of hits so far, i.e. results read from the cache
    hits: int
    #: Number of misses, i.e. freshly computed results
    misses: int
    #: The maximum number of cache entries or :py:data:`None` for an unbounded cache
    maxsize: Optional[int]
    #: The current number of cache entries
    currsize: int


@public_module("asyncstdlib.functools")
class CacheParameters(TypedDict):
    """
    Metadata on the parameters of a cache

    This is a :py:class:`~typing.TypedDict`,
    meaning it cannot be unpacked in assignments.
    """

    #: The maximum number of cache entries or :py:data:`None` for an unbounded cache
    maxsize: Optional[int]
    #: Whether values of different type are always treated as distinct
    typed: bool


@public_module("asyncstdlib.functools")
class LRUAsyncCallable(Protocol[AC]):
    """
    :py:class:`~typing.Protocol` of a LRU cache wrapping a callable to an awaitable
    """

    __slots__: Tuple[str, ...] = ()

    @property
    def __wrapped__(self) -> AC:
        """The callable wrapped by this cache"""
        raise NotImplementedError

    #: Get the result of ``await __wrapped__(...)`` from the cache or evaluation
    __call__: AC

    def cache_parameters(self) -> CacheParameters:
        """Get the parameters of the cache"""

    def cache_info(self) -> CacheInfo:
        """
        Get the current performance and boundary of the cache
        as a :py:class:`~typing.NamedTuple`
        """

    def cache_clear(self) -> None:
        """Evict all call argument patterns and their results from the cache"""

    def cache_discard(self, *args: Any, **kwargs: Any) -> None:
        """
        Evict the call argument pattern and its result from the cache

        When a cache is wrapped by another :term:`descriptor`
        (``property``, ``staticmethod``, ...),
        the descriptor must support wrapping descriptors for this method
        to detect implicit arguments such as ``self``.
        """
        # "support wrapping descriptors" means that the wrapping descriptor has to use
        # the cache as a descriptor as well, i.e. invoke its ``__get__`` method instead
        # of just passing in `self`/`cls`/... directly.


class LRUAsyncBoundCallable(LRUAsyncCallable[AC]):
    """A :py:class:`~.LRUAsyncCallable` that is bound like a method"""

    __slots__ = ("__weakref__", "_lru", "__self__")

    def __init__(self, lru: LRUAsyncCallable[AC], __self__: object):
        self._lru = lru
        self.__self__ = __self__

    @property
    def __wrapped__(self) -> AC:
        return self._lru.__wrapped__

    @property
    def __func__(self) -> LRUAsyncCallable[AC]:
        return self._lru

    def __call__(self, *args, **kwargs):  # type: ignore
        return self._lru(self.__self__, *args, **kwargs)

    def cache_parameters(self) -> CacheParameters:
        return self._lru.cache_parameters()

    def cache_info(self) -> CacheInfo:
        return self._lru.cache_info()

    def cache_clear(self) -> None:
        return self._lru.cache_clear()

    def cache_discard(self, *args: Any, **kwargs: Any) -> None:
        return self._lru.cache_discard(self.__self__, *args, **kwargs)

    def __repr__(self) -> str:
        name = getattr(self.__wrapped__, "__qualname__", "?")
        return f"<bound async cache {name} of {self.__self__}>"

    def __getattr__(self, name: str) -> Any:
        return getattr(self._lru, name)

    @property
    def __doc__(self) -> Optional[str]:  # type: ignore
        return self._lru.__doc__

    @property
    def __annotations__(self) -> Dict[str, Any]:  # type: ignore
        return self._lru.__annotations__


@overload
def lru_cache(maxsize: AC, typed: bool = ...) -> LRUAsyncCallable[AC]:
    ...


@overload
def lru_cache(
    maxsize: Optional[int] = ..., typed: bool = ...
) -> Callable[[AC], LRUAsyncCallable[AC]]:
    ...


@public_module("asyncstdlib.functools")
def lru_cache(
    maxsize: Optional[Union[int, AC]] = 128, typed: bool = False
) -> Union[LRUAsyncCallable[AC], Callable[[AC], LRUAsyncCallable[AC]]]:
    """
    Least Recently Used cache for async functions

    Applies an LRU cache storing call arguments and their *awaited* return value.
    This is appropriate for :term:`coroutine functions <coroutine function>`,
    :py:func:`~functools.partial` coroutines and any other callable that returns
    an :term:`awaitable`.

    Arguments to the cached function must be :term:`hashable`; when the arguments are
    in the cache, the underlying function is *not* called. This means any side-effects,
    including scheduling in an event loop, are skipped. Ideally, ``lru_cache`` is used
    for long-running queries or requests that return the same result for the same input.

    The maximum number of cached items is defined by ``maxsize``:

    * If set to a positive integer, up to ``maxsize`` function argument
      patterns are stored; further calls with *different* patterns replace the oldest
      pattern in the cache.

    * If set to zero or a negative integer, the cache is disabled. Every call is
      directly forwarded to the underlying function, and counted as a cache miss.

    * If set to :py:data:`None`, the cache has unlimited size. Every used function
      argument pattern adds an entry to the cache; patterns are never
      automatically evicted.

    In addition to automatic cache eviction from ``maxsize``, the cache can be
    explicitly emptied via :py:meth:`~LRUAsyncCallable.cache_clear`
    and :py:meth:`~LRUAsyncCallable.cache_discard`.
    Use the cache's :py:meth:`~LRUAsyncCallable.cache_info` to inspect the cache's
    performance and filling level.

    If ``typed`` is :py:data:`True`, values in argument patterns are compared by
    value *and* type. For example, this means ``3`` and ``3.0`` are treated as
    distinct arguments; however, this is not applied recursively so the type of
    both ``(3, 4)`` and ``(3.0, 4.0)`` is the same.

    .. note::

        This LRU cache supports overlapping ``await`` calls, provided that the
        wrapped async function does as well.
        Unlike the original :py:func:`functools.lru_cache`, it is not thread-safe.
    """
    if isinstance(maxsize, int):
        maxsize = 0 if maxsize < 0 else maxsize
    elif callable(maxsize):
        # used as function decorator, first arg is the function to be wrapped
        fast_wrapper = CachedLRUAsyncCallable(cast(AC, maxsize), typed, 128)
        return update_wrapper(fast_wrapper, maxsize)
    elif maxsize is not None:
        raise TypeError(
            "first argument to 'lru_cache' must be an int, a callable or None"
        )

    def lru_decorator(function: AC) -> LRUAsyncCallable[AC]:
        assert not callable(maxsize)
        wrapper: LRUAsyncCallable[AC]
        if maxsize is None:
            wrapper = MemoizedLRUAsyncCallable(function, typed)
        elif maxsize == 0:
            wrapper = UncachedLRUAsyncCallable(function, typed)
        else:
            wrapper = CachedLRUAsyncCallable(function, typed, maxsize)
        return update_wrapper(wrapper, function)

    return lru_decorator


class CallKey:
    """Representation of a call suitable as a ``dict`` key and for equality testing"""

    __slots__ = "_hash", "values"

    def __init__(self, values: Tuple[Hashable, ...]):
        # we may need the hash very often so caching helps
        self._hash = hash(values)
        self.values = values

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and self.values == other.values  # type: ignore

    # DEVIATION: fast_types tuple vs. set contains is faster +40%/pypy and +20%/cpython
    @classmethod
    def from_call(
        cls,
        args: Tuple[Hashable, ...],
        kwds: Dict[str, Hashable],
        typed: bool,
        fast_types: Tuple[type, ...] = (int, str),
        kwarg_sentinel: Hashable = object(),
    ) -> "Union[CallKey, int, str]":
        """
        Create a key based on call arguments

        :param args: positional call arguments
        :param kwds: keyword call arguments
        :param typed: whether to compare arguments by strict type as well
        :param fast_types: types which do not need wrapping
        :param kwarg_sentinel: internal marker, stick with default
        :return: representation of the call arguments

        The `fast_types` and `kwarg_sentinel` primarily are arguments to make them
        pre-initialised locals for speed; their defaults should be optimal already.
        """
        key = args if not kwds else (*args, kwarg_sentinel, *kwds.items())
        if typed:
            key += (
                tuple(map(type, args))
                if not kwds
                else (*map(type, args), *map(type, kwds.values()))
            )
        elif len(key) == 1 and type(key[0]) in fast_types:
            return key[0]  # type: ignore
        return cls(key)


def cache__get(
    self: LRUAsyncCallable[AC], instance: object, owner: Optional[type] = None
) -> LRUAsyncCallable[AC]:
    """Descriptor ``__get__`` for caches to bind them on lookup"""
    if instance is None:
        return self
    return LRUAsyncBoundCallable(self, instance)


class UncachedLRUAsyncCallable(LRUAsyncCallable[AC]):
    """Wrap the async ``call`` to track accesses as for caching/memoization"""

    __slots__ = ("__weakref__", "__dict__", "__wrapped__", "__misses", "__typed")

    __wrapped__: AC
    __get__ = cache__get

    def __init__(self, call: AC, typed: bool):
        self.__wrapped__ = call
        self.__misses = 0
        self.__typed = typed

    async def __call__(self, *args, **kwargs):  # type: ignore
        self.__misses += 1
        return await self.__wrapped__(*args, **kwargs)

    def cache_parameters(self) -> CacheParameters:
        return CacheParameters(maxsize=0, typed=self.__typed)

    def cache_info(self) -> CacheInfo:
        return CacheInfo(0, self.__misses, 0, 0)

    def cache_clear(self) -> None:
        self.__misses = 0

    def cache_discard(self, *args: Any, **kwargs: Any) -> None:
        return


class MemoizedLRUAsyncCallable(LRUAsyncCallable[AC]):
    """Wrap the async ``call`` with async memoization"""

    __slots__ = (
        "__weakref__",
        "__dict__",
        "__wrapped__",
        "__hits",
        "__misses",
        "__typed",
        "__cache",
    )

    __wrapped__: AC
    __get__ = cache__get

    def __init__(self, call: AC, typed: bool):
        self.__wrapped__ = call
        self.__hits = 0
        self.__misses = 0
        self.__typed = typed
        self.__cache: Dict[Union[CallKey, int, str], Any] = {}

    async def __call__(self, *args, **kwargs):  # type: ignore
        key = CallKey.from_call(args, kwargs, typed=self.__typed)
        try:
            result = self.__cache[key]
        except KeyError:
            self.__misses += 1
            result = await self.__wrapped__(*args, **kwargs)
            # function finished early for another call with the same arguments
            # the cache has been updated already, do nothing to it
            if key not in self.__cache:
                self.__cache[key] = result
            return result
        else:
            self.__hits += 1
            return result

    def cache_parameters(self) -> CacheParameters:
        return CacheParameters(maxsize=None, typed=self.__typed)

    def cache_info(self) -> CacheInfo:
        return CacheInfo(self.__hits, self.__misses, None, len(self.__cache))

    def cache_clear(self) -> None:
        self.__hits = 0
        self.__misses = 0
        self.__cache.clear()

    def cache_discard(self, *args: Any, **kwargs: Any) -> None:
        self.__cache.pop(CallKey.from_call(args, kwargs, typed=self.__typed), None)


class CachedLRUAsyncCallable(LRUAsyncCallable[AC]):
    """Wrap the async ``call`` with async LRU caching of finite capacity"""

    __slots__ = (
        "__weakref__",
        "__dict__",
        "__wrapped__",
        "__hits",
        "__misses",
        "__typed",
        "__maxsize",
        "__cache",
    )

    __wrapped__: AC
    __get__ = cache__get

    def __init__(self, call: AC, typed: bool, maxsize: int):
        self.__wrapped__ = call
        self.__hits = 0
        self.__misses = 0
        self.__typed = typed
        self.__maxsize = maxsize
        self.__cache: OrderedDict[Union[int, str, CallKey], Any] = OrderedDict()

    async def __call__(self, *args, **kwargs):  # type: ignore
        key = CallKey.from_call(args, kwargs, typed=self.__typed)
        try:
            result = self.__cache[key]
        except KeyError:
            self.__misses += 1
            result = await self.__wrapped__(*args, **kwargs)
            # function finished early for another call with the same arguments
            # the cache has been updated already, do nothing to it
            if key in self.__cache:
                pass
            # the cache is filled already
            # push the new content to the current root and rotate the list once
            elif len(self.__cache) >= self.__maxsize:
                self.__cache.popitem(last=False)
                self.__cache[key] = result
            # the cache still has room
            # insert the new element at the back
            else:
                self.__cache[key] = result
            return result
        else:
            self.__cache.move_to_end(key, last=True)
            self.__hits += 1
            return result

    def cache_parameters(self) -> CacheParameters:
        return CacheParameters(maxsize=self.__maxsize, typed=self.__typed)

    def cache_info(self) -> CacheInfo:
        return CacheInfo(self.__hits, self.__misses, self.__maxsize, len(self.__cache))

    def cache_clear(self) -> None:
        self.__hits = 0
        self.__misses = 0
        self.__cache.clear()

    def cache_discard(self, *args: Any, **kwargs: Any) -> None:
        self.__cache.pop(CallKey.from_call(args, kwargs, typed=self.__typed), None)
