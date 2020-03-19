"""
Reimplementation of ``functools.lru_cache`` as async based on CPython 3.8

This is loosely based on the CPython 3.8 implementation. In specific,
several performance hacks are skipped in favour of maintainability,
especially when they might not apply to PyPy.
"""
from typing import (
    NamedTuple,
    Callable,
    Awaitable,
    TypeVar,
    Optional,
    Tuple,
    Dict,
    Union,
)
from functools import update_wrapper
from collections import OrderedDict

from typing_extensions import Protocol

from ._utility import public_module


R = TypeVar("R")


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
class LRUAsyncCallable(Protocol[R]):
    """
    :py:class:`~typing.Protocol` of a LRU cache wrapping a callable to an awaitable
    """

    #: The callable wrapped by this cache
    __wrapped__: Callable[..., Awaitable[R]]

    async def __call__(self, *args, **kwargs) -> R:
        """Get the result of ``await __wrapped__(...)`` from the cache or evaluation"""

    def cache_info(self) -> CacheInfo:
        """Get the current performance and boundary of the cache"""

    def cache_clear(self) -> None:
        """Evict all call argument patterns and their results from the cache"""


@public_module("asyncstdlib.functools")
def lru_cache(maxsize: int = 128, typed: bool = False):
    """
    Least Recently Used cache for async functions

    Applies an LRU cache, mapping the most recent function call arguments
    to the *awaited* function return value. This makes this cache appropriate for
    :term:`coroutine functions <coroutine function>`, :py:func:`~functools.partial`
    coroutines and any other callable that returns an :term:`awaitable`.

    Arguments to the cached function must be :term:`hashable`. On a successful cache
    hit, the underlying function is *not* called. This means any side-effects, including
    scheduling in an internal event loop, are skipped. Ideally, ``lru_cache`` is used
    for long-running queries or requests that return the same result for the same input.

    The maximum number of cached items is defined by ``maxsize``:

    * If set to a positive integer, at most ``maxsize`` distinct function argument
      patterns are stored; further calls with *different* patterns evict the oldest
      stored pattern from the cache.

    * If set to zero or a negative integer, the cache is disabled. Every call is
      directly forwarded to the underlying function, and counted as a cache miss.

    * If set to :py:data:`None`, the cache has unlimited size. Every new function
      argument pattern adds an entry to the cache; patterns and values are never
      automatically evicted.

    The cache can always be explicitly emptied via
    :py:meth:`~LRUAsyncCallable.cache_clear`.
    Use the cache's :py:meth:`~LRUAsyncCallable.cache_info` to inspect the cache's
    performance and filling level.

    If ``typed`` is :py:data:`True`, values in argument patterns are compared by
    value *and* type. For example, this means that passing ``3`` and ``3.0`` as
    the same argument are treated as distinct pattern elements.

    .. note::

        This wrapper is intended for use with a single event loop, and supports
        overlapping concurrent calls.
        Unlike the original :py:func:`functools.lru_cache`, it is not thread-safe.
    """
    if isinstance(maxsize, int):
        maxsize = 0 if maxsize < 0 else maxsize
    elif callable(maxsize):
        # used as function decorator, first arg is the function to be wrapped
        fast_wrapper = _bounded_lru(function=maxsize, maxsize=128, typed=typed)
        return update_wrapper(fast_wrapper, maxsize)
    elif maxsize is not None:
        raise TypeError(
            "first argument to 'lru_cache' must be an int, a callable or None"
        )

    def lru_decorator(function: Callable[..., Awaitable[R]]) -> LRUAsyncCallable[R]:
        if maxsize is None:
            wrapper = _unbound_lru(function=function, typed=typed)
        elif maxsize == 0:
            wrapper = _empty_lru(function=function)
        else:
            wrapper = _bounded_lru(function=function, maxsize=maxsize, typed=typed)
        return update_wrapper(wrapper, function)

    return lru_decorator


class CallKey:
    __slots__ = "_hash", "values"

    def __init__(self, values):
        self._hash = hash(values)
        self.values = values

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return type(self) is type(other) and self.values == other.values

    # DEVIATION: fast_types tuple vs. set contains is faster +40%/pypy vs. +20%/cpython
    @classmethod
    def from_call(
        cls,
        args: Tuple,
        kwds: Dict,
        typed: bool,
        fast_types=(int, str),
        kwarg_sentinel=object(),
    ) -> "Union[CallKey, int, str]":
        key = args if not kwds else (*args, kwarg_sentinel, *kwds.items())
        if typed:
            key += (
                tuple(map(type, args))
                if not kwds
                else (*map(type, args), *map(type, kwds.values()))
            )
        elif len(key) == 1 and type(key[0]) in fast_types:
            return key[0]
        return cls(key)


def _empty_lru(function: Callable[..., Awaitable[R]]) -> LRUAsyncCallable[R]:
    """Wrap the async ``function`` in an async LRU cache without any capacity"""
    # cache statistics
    misses = 0

    async def wrapper(*args, **kwargs) -> R:
        nonlocal misses
        misses += 1
        return await function(*args, **kwargs)

    def cache_info() -> CacheInfo:
        return CacheInfo(0, misses, 0, 0)

    def cache_clear():
        nonlocal misses
        misses = 0

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear
    return wrapper


def _unbound_lru(
    function: Callable[..., Awaitable[R]], typed: bool
) -> LRUAsyncCallable[R]:
    """Wrap the async ``function`` in an async LRU cache with infinite capacity"""
    # local lookup
    make_key = CallKey.from_call
    # cache statistics
    hits = 0
    misses = 0
    # cache content
    cache: Dict[Union[CallKey, int, str], R] = {}

    async def wrapper(*args, **kwargs) -> R:
        nonlocal hits, misses
        key = make_key(args, kwargs, typed=typed)
        try:
            result = cache[key]
        except KeyError:
            misses += 1
            result = await function(*args, **kwargs)
            # function finished early for another call with the same arguments
            # the cache has been updated already, do nothing to it
            if key not in cache:
                cache[key] = result
            return result
        else:
            hits += 1
            return result

    def cache_info() -> CacheInfo:
        return CacheInfo(hits, misses, None, len(cache))

    def cache_clear():
        nonlocal hits, misses
        misses = 0
        hits = 0
        cache.clear()

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear
    return wrapper


def _bounded_lru(
    function: Callable[..., Awaitable[R]], typed: bool, maxsize: int,
) -> LRUAsyncCallable[R]:
    """Wrap the async ``function`` in an async LRU cache with fixed capacity"""
    # local lookup
    make_key = CallKey.from_call
    # cache statistics
    hits = 0
    misses = 0
    # cache content
    cache: OrderedDict[Union[int, str, CallKey], R] = OrderedDict()
    filled = False

    async def wrapper(*args, **kwargs) -> R:
        nonlocal hits, misses, filled
        key = make_key(args, kwargs, typed=typed)
        try:
            result = cache[key]
        except KeyError:
            misses += 1
            result = await function(*args, **kwargs)
            # function finished early for another call with the same arguments
            # the cache has been updated already, do nothing to it
            if key in cache:
                pass
            # the cache is filled already
            # push the new content to the current root and rotate the list once
            elif filled:
                cache.popitem(last=False)
                cache[key] = result
            # the cache still has room
            # insert the new element at the back
            else:
                cache[key] = result
                filled = len(cache) >= maxsize
            return result
        else:
            cache.move_to_end(key, last=True)
            hits += 1
            return result

    def cache_info() -> CacheInfo:
        return CacheInfo(hits, misses, maxsize, len(cache))

    def cache_clear():
        nonlocal hits, misses, filled
        misses = 0
        hits = 0
        filled = False
        cache.clear()

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear
    return wrapper
