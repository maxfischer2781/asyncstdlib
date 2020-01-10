from typing import Callable, TypeVar, Awaitable, Union

from ._core import ScopedIter, awaitify as _awaitify, Sentinel
from .builtins import anext, AnyIterable

from ._lrucache import lru_cache, CacheInfo, LRUAsyncCallable

__all__ = ["lru_cache", "CacheInfo", "LRUAsyncCallable", "reduce"]


T = TypeVar("T")


__REDUCE_SENTINEL = Sentinel("<no default>")


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
    async with ScopedIter(iterable) as (item_iter,):
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
