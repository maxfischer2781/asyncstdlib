from typing import (
    TypeVar,
    AsyncIterator,
    List,
    Awaitable,
    Union,
    Callable,
    Optional,
    Deque,
    Generic,
    Iterator,
    Tuple,
)
from collections import deque

from ._utility import public_module
from ._core import ScopedIter, AnyIterable, awaitify as _awaitify, Sentinel
from .builtins import anext, zip, enumerate as aenumerate, aiter as aiter

T = TypeVar("T")
S = TypeVar("S")


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
            yield current
            async for value in accumulate:
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


async def starmap(
    function: Union[Callable[..., T], Callable[..., Awaitable[T]]],
    iterable: AnyIterable,
) -> AsyncIterator[T]:
    """
    An :term:`asynchronous iterator` applying a function to arguments from an iterable

    This is conceptually similar to :py:func:`~asyncstdlib.builtins.map`, but applies
    a single iterable of multiple arguments instead of
    multiple iterables of a single argument each.
    The same way that
    ``function(a, b)`` can be generalized to ``map(function, iter_a, iter_b)``,
    ``function(*c)`` can be generalized to ``starmap(function, iter_c)``.
    """
    function = _awaitify(function)
    async with ScopedIter(iterable) as (async_iter,):
        async for args in async_iter:
            yield await function(*args)


async def takewhile(
    predicate: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]]],
    iterable: AnyIterable[T],
) -> AsyncIterator[T]:
    """
    Yield items from ``iterable`` as long as ``predicate(item)`` is true

    This lazily iterates over ``iterable``, yielding items as long as evaluating
    ``predicate`` for the current item is true. As soon as ``predicate`` evaluates
    as false for the current item, no more items are yielded. Note that if
    ``iterable`` is a single-use iterator, the item is available neither from
    ``iterable`` nor ``takewhile`` and effectively discarded.
    """
    async with ScopedIter(iterable) as (async_iter,):
        predicate = _awaitify(predicate)
        async for item in async_iter:
            if await predicate(item):
                yield item
            else:
                break


async def tee_peer(
    iterator: AsyncIterator[T], buffer: Deque[T], peers: List[Deque[T]], cleanup: bool,
) -> AsyncIterator[T]:
    while True:
        if not buffer:
            try:
                item = await iterator.__anext__()
            except StopAsyncIteration:
                break
            else:
                # Append to all buffers, including our own. We'll fetch our
                # item from the buffer again, instead of yielding it directly.
                # This ensures the proper item ordering if any of our peers
                # are fetching items concurrently. They may have buffered their
                # item already.
                for peer in peers:
                    peer.append(item)
        yield buffer.popleft()
    for idx, item in enumerate(peers):
        if item is buffer:
            peers.pop(idx)
            break
    if cleanup and not peers and hasattr(iterator, "aclose"):
        await iterator.aclose()


@public_module(__name__, "tee")
class Tee(Generic[T]):
    """
    Create ``n`` separate asynchronous iterators over ``iterable``

    This splits a single ``iterable`` into multiple iterators, each providing
    the same items in the same order.
    All child iterators may advance separately but share the same items
    from ``iterable`` -- when the most advanced iterator retrieves an item,
    it is buffered until the least advanced iterator has yielded it as well.
    A ``tee`` works lazily and can handle an infinite ``iterable``, provided
    that all iterators advance.

    .. code-block:: python3

        async def derivative(sensor_data):
            previous, current = a.tee(sensor_data, n=2)
            await a.anext(previous)  # advance one iterator
            return a.map(operator.sub, previous, current)

    Unlike :py:func:`itertools.tee`, :py:func:`~.tee` returns a custom type instead
    of a :py:class:`tuple`. Like a tuple, it can be indexed, iterated and unpacked
    to get the child iterators. In addition, its :py:meth:`~.tee.aclose` method
    immediately closes all children, and it can be used in an ``async with`` context
    for the same effect.

    If ``iterable`` is an iterator and read elsewhere, ``tee`` will *not*
    provide these items. Also, ``tee`` must internally buffer each item until the
    last iterator has yielded it; if the most and least advanced iterator differ
    by most data, using a :py:class:`list` is faster (but not lazy).

    If the underlying iterable is concurrency safe (``anext`` may be awaited
    concurrently) the resulting iterators are concurrency safe as well. Otherwise,
    the iterators are safe if there is only ever one single "most advanced" iterator.
    """

    def __init__(
        self, iterable: AnyIterable[T], n: int = 2,
    ):
        self._iterator = aiter(iterable)
        _cleanup = self._iterator is iterable
        self._buffers = [deque() for _ in range(n)]
        self._children = tuple(
            tee_peer(
                iterator=self._iterator,
                buffer=buffer,
                peers=self._buffers,
                cleanup=_cleanup,
            )
            for buffer in self._buffers
        )

    def __len__(self) -> int:
        return len(self._children)

    def __getitem__(self, item) -> AsyncIterator[T]:
        return self._children[item]

    def __iter__(self) -> Iterator[AnyIterable[T]]:
        yield from self._children

    async def __aenter__(self) -> "Tee[T]":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
        return False

    async def aclose(self):
        for child in self._children:
            await child.aclose()


tee = Tee


async def _repeat(value):
    while True:
        yield value


async def zip_longest(
    *iterables: AnyIterable[T], fillvalue: S = None
) -> AsyncIterator[Tuple[Union[T, S], ...]]:
    """
    Create an async iterator that aggregates elements from each of the (async) iterables

    The next element of ``zip_longest`` is a :py:class:`tuple` of the next element of
    each of its ``iterables``. As soon as all of its ``iterables`` are exhausted,
    ``zip_longest`` is exhausted as well. Shorter iterables are padded by ``fillvalue``.
    This means that if ``zip_longest`` receives *n* ``iterables``,
    with the longest having *m* elements, it becomes a generator *m*-times producing
    an *n*-tuple.

    If ``iterables`` is empty, the ``zip_longest`` iterator is empty as well.
    Multiple ``iterables`` may be mixed regular and async iterables.
    """
    if not iterables:
        return
    async with ScopedIter(*iterables, _repeat(fillvalue)) as (*async_iters, fill_iter):
        remaining = len(async_iters)
        while True:
            values = []
            for index, aiterator in enumerate(async_iters):
                try:
                    value = await anext(aiterator)
                except StopAsyncIteration:
                    remaining -= 1
                    if not remaining:
                        return
                    async_iters[index] = fill_iter
                    values.append(fillvalue)
                else:
                    values.append(value)
                    del value
            yield tuple(values)
