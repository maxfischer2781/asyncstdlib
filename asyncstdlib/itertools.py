from typing import TypeVar, AsyncIterator, List, Awaitable, Union, Callable, Optional

from ._utility import public_module
from ._core import ScopedIter, AnyIterable, awaitify as _awaitify
from .builtins import anext, Sentinel, zip, enumerate as aenumerate


T = TypeVar("T")


async def cycle(iterable: AnyIterable[T]) -> AsyncIterator[T]:
    """
    An :term:`asynchronous iterator` indefinitely iterating over ``iterable``

    This lazily exhausts ``iterable`` on its first pass, and recalls items
    from an internal buffer on subsequent passes. If ``iterable`` is empty,
    the resulting iterator terminates immediately.

    This means items from ``iterable`` are provided immediately as they become
    available, even if later items are not ready yet. Subsequent passes directly
    provide items, without replicating any delays of the original ``iterable``.
    All items produced by ``iterable`` are stored internally, which may consume
    significant memory.
    """
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
    """The default reduction of :py:func:`~.accumulate`"""
    return x + y


async def accumulate(
    iterable: AnyIterable[T],
    function: Union[Callable[[T, T], T], Callable[[T, T], Awaitable[T]]] = add,
    *,
    initial: T = __ACCUMULATE_SENTINEL,
) -> AsyncIterator[T]:
    """
    An :term:`asynchronous iterator` on the running reduction of ``iterable``

    :raises TypeError: if ``iterable`` is empty and ``initial`` is not given

    This is conceptually equivalent to :py:func:`~asyncstdlib.functools.reduce`
    in that it applies a reduction ``function`` iteratively on the ``iterable``.
    However, the iterator yields the *running* reduction value as each value
    is fetched from ``iterable``.

    The ``function`` defaults to ``operator.add``, providing a running sum.
    If an ``initial`` value is provided, it is the first value processed and yielded.
    Provided that all parameters are given and valid, this is roughly equivalent to:

    .. code-block:: python3

        async def accumulate(iterable, function, *, initial):
            current = initial
            async for value in accumulate:
                yield current
                current = await function(current, value)
            yield current
    """
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
        yield value
        async for head in item_iter:
            value = await function(value, head)
            yield value


async def chain(*iterables: AnyIterable[T]) -> AsyncIterator[T]:
    """
    An :term:`asynchronous iterator` flattening values from all ``iterables``

    The resulting iterator consecutively iterates over and yields all values from
    each of the ``iterables``. This is similar to converting all ``iterables`` to
    sequences and concatenating them, but lazily exhausts each iterable.
    """
    async with ScopedIter(*iterables) as iterators:
        for iterator in iterators:
            async for item in iterator:
                yield item


@public_module(__name__, "chain.from_iterable")
async def chain_from_iterable(
    iterable: AnyIterable[AnyIterable[T]],
) -> AsyncIterator[T]:
    """
    Alternate constructor for :py:func:`~.chain` that lazily exhausts iterables as well
    """
    async with ScopedIter(iterable) as (iterables,):
        async for sub_iterable in iterables:
            async with ScopedIter(sub_iterable) as (iterator,):
                async for item in iterator:
                    yield item


chain.from_iterable = chain_from_iterable


async def compress(
    data: AnyIterable[T], selectors: AnyIterable[bool]
) -> AsyncIterator[T]:
    """
    An :term:`asynchronous iterator` for items of ``data`` with true ``selectors``

    Lazily iterates both ``data`` and ``selectors`` pairwise, yielding only ``data``
    items for which their paired ``selectors`` evaluate as true.
    Roughly equivalent to:

    .. code-block:: python3

        async def compress(data, selectors):
            return (item async for item, select in zip(data, selectors) if select)
    """
    async with ScopedIter(data, selectors) as (data_iter, selectors_iter):
        async for item, keep in zip(data_iter, selectors_iter):
            if keep:
                yield item


async def dropwhile(
    predicate: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]]],
    iterable: AnyIterable[T],
) -> AsyncIterator[T]:
    """
    Yield items from ``iterable`` after ``predicate(item)`` is no longer true

    This lazily iterates over ``iterable``, discarding items as long as evaluating
    ``predicate`` for the current item is true. As soon as ``predicate`` evaluates
    as true for the current item, this item is yielded. All subsequent items are
    yielded immediately as they become available, without evaluating ``predicate``
    for them.
    """
    async with ScopedIter(iterable) as (async_iter,):
        predicate = _awaitify(predicate)
        async for item in async_iter:
            if not await predicate(item):  # type: ignore
                yield item
                break
        async for item in async_iter:
            yield item


async def islice(iterable: AnyIterable[T], *args: Optional[int]) -> AsyncIterator[T]:
    """
    An :term:`asynchronous iterator` over items from ``iterable`` in a :py:class:`slice`

    Aside from the iterable, this function accepts one to three parameters as understood
    by :py:class:`slice`:
    a single parameter ``stop``, or up to three parameters ``start, stop [, step]``.
    The first ``start`` items of ``iterable`` are discarded. Afterwards, each ``step``
    item is yielded until a total of ``stop`` items have been fetched. This effectively
    is a lazy, asynchronous version of ``iterable[start:stop:step]``.
    """
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
