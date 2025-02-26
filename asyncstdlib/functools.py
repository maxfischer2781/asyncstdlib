from asyncio import iscoroutinefunction
from typing import (
    Callable,
    Awaitable,
    Union,
    Any,
    Generic,
    Generator,
    Optional,
    AsyncContextManager,
    Type,
    cast,
)

from ._typing import T, AC, AnyIterable, R
from ._core import ScopedIter, awaitify as _awaitify, Sentinel
from .builtins import anext
from .contextlib import nullcontext

from ._lrucache import (
    lru_cache,
    CacheInfo,
    CacheParameters,
    LRUAsyncCallable,
    LRUAsyncBoundCallable,
)

__all__ = [
    "cache",
    "lru_cache",
    "CacheInfo",
    "CacheParameters",
    "LRUAsyncCallable",
    "LRUAsyncBoundCallable",
    "reduce",
    "cached_property",
    "CachedProperty",
]


def cache(user_function: AC) -> LRUAsyncCallable[AC]:
    """
    Simple unbounded cache, aka memoization,  for async functions

    This is a convenience function, equivalent to :py:func:`~.lru_cache`
    with a ``maxsize`` of :py:data:`None`.
    """
    return lru_cache(maxsize=None)(user_function)


class AwaitableValue(Generic[R]):
    """Helper to provide an arbitrary value in ``await``"""

    __slots__ = ("value",)

    def __init__(self, value: R):
        self.value = value

    # noinspection PyUnreachableCode
    def __await__(self) -> Generator[None, None, R]:
        return self.value
        yield  # type: ignore # pragma: no cover

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"


class _FutureCachedPropertyValue(Generic[R, T]):
    """
    A placeholder object to control concurrent access to a cached awaitable value

    When given a lock to coordinate access, only the first task to await on a
    cached property triggers the underlying coroutine. Once a value has been
    produced, all tasks are unblocked and given the same, single value.
    """

    __slots__ = ("_func", "_instance", "_name", "_lock")

    def __init__(
        self,
        func: Callable[[T], Awaitable[R]],
        instance: T,
        name: str,
        lock: AsyncContextManager[Any],
    ):
        self._func = func
        self._instance = instance
        self._name = name
        self._lock = lock

    def __await__(self) -> Generator[None, None, R]:
        return self._await_impl().__await__()

    @property
    def _instance_value(self) -> Awaitable[R]:
        """Retrieve whatever is currently cached on the instance

        If the instance (no longer) has this attribute, it was deleted and the
        process is restarted by delegating to the descriptor.
        """
        try:
            return self._instance.__dict__[self._name]
        except KeyError:
            # something deleted the cached value or future cached value placeholder. Restart
            # the fetch by delegating to the cached_property descriptor.
            return getattr(self._instance, self._name)

    async def _await_impl(self) -> R:
        if (stored := self._instance_value) is self:
            # attempt to get the lock
            async with self._lock:
                # check again for a cached value
                if (stored := self._instance_value) is self:
                    # the instance attribute is still this placeholder, and we
                    # hold the lock. Start the getter to store the value on the
                    # instance and return the value.
                    return await self._get_attribute()

        # another task produced a value, or the instance.__dict__ object was
        # deleted in the interim.
        return await stored

    async def _get_attribute(self) -> R:
        value = await self._func(self._instance)
        self._instance.__dict__[self._name] = AwaitableValue(value)
        return value

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} for '{type(self._instance).__name__}."
            f"{self._name}' at {id(self):#x}>"
        )


class CachedProperty(Generic[T, R]):
    def __init__(
        self,
        getter: Callable[[T], Awaitable[R]],
        asynccontextmanager_type: Type[AsyncContextManager[Any]] = nullcontext,
    ):
        self.func = self.__wrapped__ = getter
        self.attrname = None
        self.__doc__ = getter.__doc__
        self.__module__ = getter.__module__
        self._asynccontextmanager_type = asynccontextmanager_type

    def __set_name__(self, owner: Any, name: str) -> None:
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                f"({self.attrname!r} and {name!r})."
            )

    def __get__(
        self, instance: Optional[T], owner: Optional[Type[Any]]
    ) -> Union["CachedProperty[T, R]", Awaitable[R]]:
        if instance is None:
            return self

        name = self.attrname
        if name is None:
            raise TypeError(
                "Cannot use cached_property instance without calling __set_name__ on it."
            )

        # check for write access first; not all objects have __dict__ (e.g. class defines slots)
        try:
            cache = instance.__dict__
        except AttributeError:
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {name!r} property."
            )
            raise TypeError(msg) from None

        # store a placeholder for other tasks to access the future cached value
        # on this instance. It takes care of coordinating between different
        # tasks awaiting on the placeholder until the cached value has been
        # produced.
        wrapper = _FutureCachedPropertyValue(
            self.func, instance, name, self._asynccontextmanager_type()
        )
        cache[name] = wrapper
        return wrapper


def cached_property(
    type_or_getter: Union[Type[AsyncContextManager[Any]], Callable[[T], Awaitable[R]]],
    /,
) -> Union[
    Callable[[Callable[[T], Awaitable[R]]], CachedProperty[T, R]],
    CachedProperty[T, R],
]:
    """
    Transform a method into an attribute whose value is cached

    When applied to an asynchronous method of a class, instances have an attribute
    of the same name as the method (similar to :py:class:`property`). Using this
    attribute with ``await`` provides the value of using the method with ``await``.

    The attribute value is cached on the instance after being computed;
    subsequent uses of the attribute with ``await`` provide the cached value,
    without executing the method again.
    The cached value can be cleared using ``del``, in which case the next
    access will recompute the value using the wrapped method.

    .. code-block:: python3

        import asyncstdlib as a

        class Resource:
            def __init__(self, url):
                self.url = url

            @a.cached_property
            async def data(self):
                return await asynclib.get(self.url)

        resource = Resource("http://example.com")
        print(await resource.data)  # needs some time...
        print(await resource.data)  # finishes instantly
        del resource.data
        print(await resource.data)  # needs some time...

    Unlike a :py:class:`property`, this type does not support
    :py:meth:`~property.setter` or :py:meth:`~property.deleter`.

    If the attribute is accessed by multiple tasks before a cached value has
    been produced, the getter can be run more than once. The final cached value
    is determined by the last getter coroutine to return. To enforce that the
    getter is executed at most once, provide an appropriate lock type - e.g. the
    :py:class:`asyncio.Lock` class in an :py:mod:`asyncio` application - and
    access is automatically synchronised.

    .. code-block:: python3

        from asyncio import Lock, gather

        class Resource:
            def __init__(self, url):
                self.url = url

            @a.cached_property(Lock)
            async def data(self):
                return await asynclib.get(self.url)

        resource = Resource("http://example.com")
        print(*(await gather(resource.data, resource.data)))

    .. note::

        Instances on which a value is to be cached must have a
        ``__dict__`` attribute that is a mutable mapping.
    """
    if iscoroutinefunction(type_or_getter):
        return CachedProperty(type_or_getter)
    elif isinstance(type_or_getter, type) and issubclass(
        type_or_getter, AsyncContextManager
    ):

        def decorator(
            coroutine: Callable[[T], Awaitable[R]],
        ) -> CachedProperty[T, R]:
            return CachedProperty(
                coroutine,
                asynccontextmanager_type=cast(
                    Type[AsyncContextManager[Any]], type_or_getter
                ),
            )

        return decorator
    else:
        raise ValueError("cached_property can only be used with a coroutine function")


__REDUCE_SENTINEL = Sentinel("<no default>")


async def reduce(
    function: Union[Callable[[T, T], T], Callable[[T, T], Awaitable[T]]],
    iterable: AnyIterable[T],
    initial: T = __REDUCE_SENTINEL,  # type: ignore
) -> T:
    """
    Reduce an (async) iterable by cumulative application of an (async) function

    :raises TypeError: if ``iterable`` is empty and ``initial`` is not given

    Applies the ``function`` from the beginning of ``iterable``, as if executing
    ``await function(current, anext(iterable))`` until ``iterable`` is exhausted.
    Note that the output of ``function`` should be valid as its first input.

    The optional ``initial`` is prepended to all items of ``iterable``
    when applying ``function``. If the combination of ``initial``
    and ``iterable`` contains exactly one item, it is returned without
    calling ``function``.
    """
    async with ScopedIter(iterable) as item_iter:
        try:
            value = (
                initial if initial is not __REDUCE_SENTINEL else await anext(item_iter)
            )
        except StopAsyncIteration:
            raise TypeError(
                "reduce() of empty sequence with no initial value"
            ) from None
        function = _awaitify(function)
        async for head in item_iter:
            value = await function(value, head)
    return value
