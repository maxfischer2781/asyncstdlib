from typing import (
    Callable,
    Awaitable,
    Union,
    Any,
    Generic,
    Generator,
    Optional,
    Coroutine,
    overload,
)

from ._typing import T, AC, AnyIterable
from ._core import ScopedIter, awaitify as _awaitify, Sentinel
from .builtins import anext
from ._utility import public_module

from ._lrucache import lru_cache, CacheInfo, CacheParameters, LRUAsyncCallable

__all__ = [
    "cache",
    "lru_cache",
    "CacheInfo",
    "CacheParameters",
    "LRUAsyncCallable",
    "reduce",
    "cached_property",
]


def cache(user_function: AC) -> LRUAsyncCallable[AC]:
    """
    Simple unbounded cache, aka memoization,  for async functions

    This is a convenience function, equivalent to :py:func:`~.lru_cache`
    with a ``maxsize`` of :py:data:`None`.
    """
    return lru_cache(maxsize=None)(user_function)


__REDUCE_SENTINEL = Sentinel("<no default>")


class AwaitableValue(Generic[T]):
    """Helper to provide an arbitrary value in ``await``"""

    __slots__ = ("value",)

    def __init__(self, value: T):
        self.value = value

    # noinspection PyUnreachableCode
    def __await__(self) -> Generator[None, None, T]:
        return self.value
        yield  # type: ignore # pragma: no cover

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"


class _RepeatableCoroutine(Generic[T]):
    """Helper to ``await`` a coroutine also more or less than just once"""

    __slots__ = ("call", "args", "kwargs")

    def __init__(
        self, __call: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any
    ):
        self.call = __call
        self.args = args
        self.kwargs = kwargs

    def __await__(self) -> Generator[Any, Any, T]:
        return self.call(*self.args, **self.kwargs).__await__()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} object {self.call.__name__} at {id(self)}>"


@public_module(__name__, "cached_property")
class CachedProperty(Generic[T]):
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

        resource = Resource(1, 3)
        print(await resource.data)  # needs some time...
        print(await resource.data)  # finishes instantly
        del resource.data
        print(await resource.data)  # needs some time...

    Unlike a :py:class:`property`, this type does not support
    :py:meth:`~property.setter` or :py:meth:`~property.deleter`.

    .. note::

        Instances on which a value is to be cached must have a
        ``__dict__`` attribute that is a mutable mapping.
    """

    def __init__(self, getter: Callable[[Any], Awaitable[T]]):
        self.__wrapped__ = getter
        self._name = getter.__name__
        self.__doc__ = getter.__doc__

    def __set_name__(self, owner: Any, name: str) -> None:
        # Check whether we can store anything on the instance
        # Note that this is a failsafe, and might fail ugly.
        # People who are clever enough to avoid this heuristic
        # should also be clever enough to know the why and what.
        if not any("__dict__" in dir(cls) for cls in owner.__mro__):
            raise TypeError(
                "'cached_property' requires '__dict__' "
                f"on {owner.__name__!r} to store {name}"
            )
        self._name = name

    @overload
    def __get__(self, instance: None, owner: type) -> "CachedProperty[T]":
        ...

    @overload
    def __get__(self, instance: object, owner: Optional[type]) -> Awaitable[T]:
        ...

    def __get__(
        self, instance: Optional[object], owner: Optional[type]
    ) -> Union["CachedProperty[T]", Awaitable[T]]:
        if instance is None:
            return self
        return _RepeatableCoroutine(self._get_attribute, instance)

    async def _get_attribute(self, instance: object) -> T:
        value = await self.__wrapped__(instance)
        instance.__dict__[self._name] = AwaitableValue(value)
        return value


cached_property = CachedProperty


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
