from typing import TypeVar, AsyncIterator, List, Awaitable, Union, Callable, Optional

from ._utility import public_module
from ._core import ScopedIter, AnyIterable, awaitify as _awaitify
from .builtins import anext, Sentinel, zip, enumerate as aenumerate


T = TypeVar("T")


async def cycle(iterable: AnyIterable[T]) -> AsyncIterator[T]:
    buffer: List[T] = []
    async with ScopedIter(iterable) as (async_iter,):
        async for item in async_iter:  # type: T
            buffer.append(item)
            yield item
    if not buffer:
        return
    while True:
        for item in buffer:
            yield item


__ACCUMULATE_SENTINEL = Sentinel("<no default>")


async def add(x, y):
    return x + y


async def accumulate(
    iterable: AnyIterable[T],
    function: Union[Callable[[T, T], T], Callable[[T, T], Awaitable[T]]] = add,
    *,
    initial: T = __ACCUMULATE_SENTINEL,
) -> AsyncIterator[T]:
    async with ScopedIter(iterable) as (item_iter,):
        try:
            value = (
                initial
                if initial is not __ACCUMULATE_SENTINEL
                else await anext(item_iter)
            )
        except StopAsyncIteration:
            raise TypeError("accumulate() of empty sequence with no initial value")
        function = _awaitify(function)
        async for head in item_iter:
            yield value
            value = await function(value, head)
        yield value


async def chain(*iterables: AnyIterable[T]) -> AsyncIterator[T]:
    async with ScopedIter(*iterables) as iterators:
        for iterator in iterators:
            async for item in iterator:
                yield item


@public_module(__name__, "chain.from_iterable")
async def chain_from_iterable(
    iterable: AnyIterable[AnyIterable[T]],
) -> AsyncIterator[T]:
    async with ScopedIter(iterable) as (iterables,):
        async for sub_iterable in iterables:
            async with ScopedIter(sub_iterable) as (iterator,):
                async for item in iterator:
                    yield item


chain.from_iterable = chain_from_iterable


async def compress(
    data: AnyIterable[T], selectors: AnyIterable[bool]
) -> AsyncIterator[T]:
    async with ScopedIter(data, selectors) as (data_iter, selectors_iter):
        async for item, keep in zip(data_iter, selectors_iter):
            if keep:
                yield item


async def dropwhile(predicate, iterable: AnyIterable[T]) -> AsyncIterator[T]:
    async with ScopedIter(iterable) as (async_iter,):
        predicate = _awaitify(predicate)
        async for item in async_iter:
            if not await predicate(item):  # type: ignore
                yield item
                break
        async for item in async_iter:
            yield item


async def islice(iterable: AnyIterable[T], *args: Optional[int]):
    s = slice(*args)
    start, stop, step = s.start or 0, s.stop, s.step or 1
    async with ScopedIter(iterable) as (async_iter,):
        # always consume the first ``start - 1`` items, even if the slice is empty
        if start > 0:
            async for _count, element in aenumerate(async_iter, start=1):
                if _count == start:
                    break
        if stop is None:
            async for idx, element in aenumerate(async_iter, start=start):
                if idx % step == 0:
                    yield element
        else:
            async for idx, element in aenumerate(async_iter, start=start):
                if idx >= stop:
                    return
                if not idx % step:
                    yield element
