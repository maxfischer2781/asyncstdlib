from typing import Callable, TypeVar, Awaitable, Union

from .builtins import iter, anext, AnyIterable, Sentinel


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

    The optional ``initial`` is the prepended to all items of ``iterable``
    when applying ``function``. If the combination of ``initial``
    and ``iterable`` contains exactly one item, it is returned without
    calling ``function``.
    """
    item_iter = iter(iterable)
    try:
        value = initial if initial is not __REDUCE_SENTINEL else await anext(item_iter)
    except StopAsyncIteration:
        raise TypeError("reduce() of empty sequence with no initial value")
    try:
        head = await anext(item_iter)
    except StopAsyncIteration:
        return value
    else:
        value = function(value, head)
    if isinstance(value, Awaitable):
        async for head in item_iter:
            value = function(await value, head)
        return await value
    else:
        async for head in item_iter:
            value = function(value, head)
        return value
