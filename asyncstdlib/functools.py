from typing import Callable, TypeVar, Awaitable, Union, Any

from ._core import ScopedIter, awaitify as _awaitify, Sentinel
from .builtins import anext, AnyIterable
from ._utility import public_module

from ._lrucache import lru_cache, CacheInfo, LRUAsyncCallable

__all__ = ["lru_cache", "CacheInfo", "LRUAsyncCallable", "reduce", "cached_property"]


T = TypeVar("T")


__REDUCE_SENTINEL = Sentinel("<no default>")


class AwaitableValue:
    """Helper to provide an arbitrary value in ``await``"""

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    # noinspection PyUnreachableCode
    def __await__(self):
        return self.value
        yield  # pragma: no cover

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value!r})"


@public_module(__name__, "cached_property")
class CachedProperty:
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

    def __set_name__(self, owner, name):
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

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self._get_attribute(instance)

    async def _get_attribute(self, instance) -> T:
        attributes = instance.__dict__
        try:
            return attributes[self._name]
        except KeyError:
            value = await self.__wrapped__(instance)
            if self._name not in attributes:
                attributes[self._name] = AwaitableValue(value)
            return value


cached_property = CachedProperty


async def reduce(
    function: Union[Callable[[T, T], T], Callable[[T, T], Awaitable[T]]],
    iterable: AnyIterable[T],
    initial: T = __REDUCE_SENTINEL,
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
            raise TypeError("reduce() of empty sequence with no initial value")
        function = _awaitify(function)
        async for head in item_iter:
            value = await function(value, head)
        return value
