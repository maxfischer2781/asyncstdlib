from typing import (
    Any,
    TypeVar,
    AsyncIterator,
    List,
    Awaitable,
    Union,
    Callable,
    Optional,
    Deque,
    Generic,
    Iterable,
    Iterator,
    Tuple,
    overload,
    AsyncGenerator,
)
from collections import deque

from ._typing import T, R, T1, T2, T3, T4, T5, AnyIterable, ADD, AsyncContextManager
from ._utility import public_module
from ._core import (
    ScopedIter,
    awaitify as _awaitify,
    Sentinel,
    borrow as _borrow,
)
from .builtins import (
    anext,
    zip,
    enumerate as aenumerate,
    iter as aiter,
    tuple as atuple,
)

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
    async with ScopedIter(iterable) as async_iter:
        async for item in async_iter:  # type: T
            buffer.append(item)
            yield item
    if not buffer:
        return
    while True:
        for item in buffer:
            yield item


__ACCUMULATE_SENTINEL = Sentinel("<no default>")


async def add(x: ADD, y: ADD) -> ADD:
    """The default reduction of :py:func:`~.accumulate`"""
    return x + y


@overload
def accumulate(iterable: AnyIterable[ADD]) -> AsyncIterator[ADD]:
    ...


@overload
def accumulate(iterable: AnyIterable[ADD], *, initial: ADD) -> AsyncIterator[ADD]:
    ...


@overload
def accumulate(
    iterable: AnyIterable[T],
    function: Union[Callable[[T, T], T], Callable[[T, T], Awaitable[T]]],
) -> AsyncIterator[T]:
    ...


@overload
def accumulate(
    iterable: AnyIterable[T],
    function: Union[Callable[[T, T], T], Callable[[T, T], Awaitable[T]]],
    *,
    initial: T,
) -> AsyncIterator[T]:
    ...


async def accumulate(
    iterable: AnyIterable[Any],
    function: Union[
        Callable[[Any, Any], Any], Callable[[Any, Any], Awaitable[Any]]
    ] = add,
    *,
    initial: Any = __ACCUMULATE_SENTINEL,
) -> AsyncIterator[Any]:
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
    async with ScopedIter(iterable) as item_iter:
        try:
            value = (
                initial
                if initial is not __ACCUMULATE_SENTINEL
                else await anext(item_iter)
            )
        except StopAsyncIteration:
            raise TypeError(
                "accumulate() of empty sequence with no initial value"
            ) from None
        function = _awaitify(function)
        yield value
        async for head in item_iter:
            value = await function(value, head)
            yield value


async def batched(iterable: AnyIterable[T], n: int) -> AsyncIterator[Tuple[T, ...]]:
    """
    Batch the ``iterable`` to tuples of the length ``n``.

    This lazily exhausts ``iterable`` and returns each batch as soon as it's ready.
    """
    if n < 1:
        raise ValueError("n must be at least one")
    async with ScopedIter(iterable) as item_iter:
        # TODO: Use walrus when 3.8 is minimal version
        # while batch := await atuple(islice(item_iter, n)):
        while True:
            batch = await atuple(islice(_borrow(item_iter), n))
            if batch:
                yield batch
            else:
                break


class chain(AsyncIterator[T]):
    """
    An :term:`asynchronous iterator` flattening values from all ``iterables``

    The resulting iterator consecutively iterates over and yields all values from
    each of the ``iterables``. This is similar to converting all ``iterables`` to
    sequences and concatenating them, but lazily exhausts each iterable.

    The ``chain`` assumes ownership of its ``iterables`` and closes them reliably
    when the ``chain`` is closed. Pass the ``iterables`` via a :py:class:`tuple` to
    ``chain.from_iterable`` to avoid closing all iterables but those already processed.
    """

    __slots__ = ("_iterator", "_owned_iterators")

    @staticmethod
    async def _chain_iterator(
        any_iterables: AnyIterable[AnyIterable[T]],
    ) -> AsyncGenerator[T, None]:
        async with ScopedIter(any_iterables) as iterables:
            async for iterable in iterables:
                async with ScopedIter(iterable) as iterator:
                    async for item in iterator:
                        yield item

    def __init__(
        self, *iterables: AnyIterable[T], _iterables: AnyIterable[AnyIterable[T]] = ()
    ):
        self._iterator = self._chain_iterator(iterables or _iterables)
        self._owned_iterators = (
            iterable
            for iterable in iterables
            if isinstance(iterable, AsyncIterator) and hasattr(iterable, "aclose")
        )

    @classmethod
    def from_iterable(cls, iterable: AnyIterable[AnyIterable[T]]) -> "chain[T]":
        """
        Alternate constructor for :py:func:`~.chain` that lazily exhausts
        the ``iterable`` of iterables as well

        This is suitable for chaining iterables from a lazy or infinite ``iterable``.
        In turn, closing the ``chain`` only closes those iterables
        already fetched from ``iterable``.
        """
        return cls(_iterables=iterable)

    def __anext__(self) -> Awaitable[T]:
        return self._iterator.__anext__()

    async def aclose(self) -> None:
        for iterable in self._owned_iterators:
            if hasattr(iterable, "aclose"):
                await iterable.aclose()
        await self._iterator.aclose()


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
    async with ScopedIter(data) as data_iter, ScopedIter(selectors) as selectors_iter:
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
    async with ScopedIter(iterable) as async_iter:
        predicate = _awaitify(predicate)
        async for item in async_iter:
            if not await predicate(item):
                yield item
                break
        async for item in async_iter:
            yield item


async def filterfalse(
    predicate: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]], None],
    iterable: AnyIterable[T],
) -> AsyncIterator[T]:
    """
    Yield items from ``iterable`` for which ``predicate(item)`` is false.

    If ``predicate`` is ``None``, return items which are false.

    Lazily iterates over ``iterable``, yielding only items for which
    ``predicate`` of the current item is false.
    """
    async with ScopedIter(iterable) as async_iter:
        if predicate is None:
            predicate = bool
        predicate = _awaitify(predicate)
        async for item in async_iter:
            if not await predicate(item):
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
    async with ScopedIter(iterable) as async_iter:
        # always consume the first ``start`` items, even if the slice is empty
        if start > 0:
            async for _count, element in aenumerate(_borrow(async_iter), start=1):
                if _count == start:
                    break
        if stop is None:
            async for idx, element in aenumerate(async_iter, start=0):
                if not idx % step:
                    yield element
        elif stop <= start:
            return
        else:
            # We would actually check ``idx >= stop -1`` later on.
            # Since we do that for every ``idx``, we subtract ``1`` once here.
            stop -= start + 1
            async for idx, element in aenumerate(async_iter, start=0):
                if not idx % step:
                    yield element
                if idx >= stop:
                    return


async def starmap(
    function: Union[Callable[..., T], Callable[..., Awaitable[T]]],
    iterable: AnyIterable[Iterable[Any]],
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
    async with ScopedIter(iterable) as async_iter:
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
    async with ScopedIter(iterable) as async_iter:
        predicate = _awaitify(predicate)
        async for item in async_iter:
            if await predicate(item):
                yield item
            else:
                break


class NoLock:
    """Dummy lock that provides the proper interface but no protection"""

    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        return False


async def tee_peer(
    iterator: AsyncIterator[T],
    # the buffer specific to this peer
    buffer: Deque[T],
    # the buffers of all peers, including our own
    peers: List[Deque[T]],
    lock: AsyncContextManager[Any],
) -> AsyncGenerator[T, None]:
    """An individual iterator of a :py:func:`~.tee`"""
    try:
        while True:
            if not buffer:
                async with lock:
                    # Another peer produced an item while we were waiting for the lock.
                    # Proceed with the next loop iteration to yield the item.
                    if buffer:
                        continue
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
                        for peer_buffer in peers:
                            peer_buffer.append(item)
            yield buffer.popleft()
    finally:
        # this peer is done – remove its buffer
        for idx, peer_buffer in enumerate(peers):  # pragma: no branch
            if peer_buffer is buffer:
                peers.pop(idx)
                break
        # if we are the last peer, try and close the iterator
        if not peers and hasattr(iterator, "aclose"):
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
    by most data, using a :py:class:`list` is more efficient (but not lazy).

    If the underlying iterable is concurrency safe (``anext`` may be awaited
    concurrently) the resulting iterators are concurrency safe as well. Otherwise,
    the iterators are safe if there is only ever one single "most advanced" iterator.
    To enforce sequential use of ``anext``, provide a ``lock``
    - e.g. an :py:class:`asyncio.Lock` instance in an :py:mod:`asyncio` application -
    and access is automatically synchronised.
    """

    def __init__(
        self,
        iterable: AnyIterable[T],
        n: int = 2,
        *,
        lock: Optional[AsyncContextManager[Any]] = None,
    ):
        self._iterator = aiter(iterable)
        self._buffers: List[Deque[T]] = [deque() for _ in range(n)]
        self._children = tuple(
            tee_peer(
                iterator=self._iterator,
                buffer=buffer,
                peers=self._buffers,
                lock=lock if lock is not None else NoLock(),
            )
            for buffer in self._buffers
        )

    def __len__(self) -> int:
        return len(self._children)

    @overload
    def __getitem__(self, item: int) -> AsyncIterator[T]:
        ...

    @overload
    def __getitem__(self, item: slice) -> Tuple[AsyncIterator[T], ...]:
        ...

    def __getitem__(
        self, item: Union[int, slice]
    ) -> Union[AsyncIterator[T], Tuple[AsyncIterator[T], ...]]:
        return self._children[item]

    def __iter__(self) -> Iterator[AnyIterable[T]]:
        yield from self._children

    async def __aenter__(self) -> "Tee[T]":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        await self.aclose()
        return False

    async def aclose(self) -> None:
        for child in self._children:
            await child.aclose()


tee = Tee


async def pairwise(iterable: AnyIterable[T]) -> AsyncIterator[Tuple[T, T]]:
    """
    Yield successive, overlapping pairs of items from ``iterable``

    Pairs are yielded as the newest item is available from ``iterable``. No pair
    is emitted if ``iterable`` has one or zero items; however, if there is one item
    ``pairwise`` will wait for and consume it before finishing.
    """
    async with ScopedIter(iterable) as async_iter:
        # any default is fine – we never yield it if there are not at least two items
        prev = await anext(async_iter, None)
        async for current in async_iter:
            yield prev, current  # type: ignore
            prev = current


async def _repeat(value: T) -> AsyncIterator[T]:
    while True:
        yield value


@overload
def zip_longest(
    __it1: AnyIterable[T1],
    *,
    fillvalue: S = ...,
) -> AsyncIterator[Tuple[T1]]:
    ...


@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    *,
    fillvalue: S = ...,
) -> AsyncIterator[Tuple[Union[T1, S], Union[T2, S]]]:
    ...


@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    *,
    fillvalue: S = ...,
) -> AsyncIterator[Tuple[Union[T1, S], Union[T2, S], Union[T3, S]]]:
    ...


@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    *,
    fillvalue: S = ...,
) -> AsyncIterator[Tuple[Union[T1, S], Union[T2, S], Union[T3, S], Union[T4, S]]]:
    ...


@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    __it5: AnyIterable[T5],
    *,
    fillvalue: S = ...,
) -> AsyncIterator[
    Tuple[Union[T1, S], Union[T2, S], Union[T3, S], Union[T4, S], Union[T5, S]]
]:
    ...


@overload
def zip_longest(
    __it1: AnyIterable[Any],
    __it2: AnyIterable[Any],
    __it3: AnyIterable[Any],
    __it4: AnyIterable[Any],
    __it5: AnyIterable[Any],
    *iterables: AnyIterable[Any],
    fillvalue: S = ...,
) -> AsyncIterator[Tuple[Any, ...]]:
    ...


async def zip_longest(
    *iterables: AnyIterable[Any], fillvalue: Any = None
) -> AsyncIterator[Tuple[Any, ...]]:
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
    fill_iter = aiter(_repeat(fillvalue))
    async_iters = [aiter(it) for it in iterables]
    del iterables
    try:
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
    finally:
        await fill_iter.aclose()  # type: ignore
        for iterator in async_iters:
            try:
                aclose = iterator.aclose()  # type: ignore
            except AttributeError:
                pass
            else:
                await aclose


async def identity(x: T) -> T:
    """Asynchronous identity function, returns its argument unchanged"""
    return x


@overload  # noqa: F811
def groupby(  # noqa: F811
    iterable: AnyIterable[T],
) -> AsyncIterator[Tuple[T, AsyncIterator[T]]]:
    ...


@overload  # noqa: F811
def groupby(  # noqa: F811
    iterable: AnyIterable[T], key: None
) -> AsyncIterator[Tuple[T, AsyncIterator[T]]]:
    ...


@overload  # noqa: F811
def groupby(  # noqa: F811
    iterable: AnyIterable[T], key: Union[Callable[[T], R], Callable[[T], Awaitable[R]]]
) -> AsyncIterator[Tuple[R, AsyncIterator[T]]]:
    ...


async def groupby(  # noqa: F811
    iterable: AnyIterable[Any],
    key: Optional[
        Union[Callable[[Any], Any], Callable[[Any], Awaitable[Any]]]
    ] = identity,
) -> AsyncIterator[Tuple[Any, AsyncIterator[Any]]]:
    """
    Create an async iterator over consecutive keys and groups from the (async) iterable

    The groups generated by ``groupby`` are consecutive with respect to the original
    (async) iterable. That is, multiple groups may have the same key if there is any
    intermediate group with different key. For example, the iterable
    ``1, 1, 1, 2, 2, 1`` is split into the groups ``1, 2, 1``.

    The async iterator returned by ``groupby`` as well as the async iterators of
    each group share the same underlying iterator. This means that previous groups
    are no longer accessible if the ``groubpy`` iterator advances to the next group.
    In specific, it is not safe to concurrently advance both the ``groupby`` iterator
    itself and any of its group iterators.

    In contrast to the original :py:func:`itertools.groupby`, it is generally not
    useful to sort ``iterable`` by ``key`` beforehand. Since both values and keys are
    required up-front for sorting, this loses the advantage of asynchronous,
    lazy iteration and evaluation.
    """
    # whether the current group was exhausted and the next begins already
    exhausted = False
    # `current_*`: buffer for key/value the current group peeked beyond its end
    current_key = current_value = nothing = object()  # type: Any
    make_key: Callable[[Any], Awaitable[Any]] = (
        _awaitify(key) if key is not None else identity  # type: ignore
    )
    async with ScopedIter(iterable) as async_iter:
        # fast-forward mode: advance to the next group
        async def seek_group() -> AsyncIterator[Any]:
            nonlocal current_value, current_key, exhausted
            # Note: `value` always ends up being some T
            # - value is something: we can never unset it
            # - value is `nothing`: the previous group was not exhausted,
            #                       and we scan at least one new value
            value: Any = current_value
            if not exhausted:
                previous_key = current_key
                while previous_key == current_key:
                    value = await anext(async_iter)
                    current_key = await make_key(value)
            current_value = nothing
            exhausted = False
            return group(current_key, value=value)

        # the lazy iterable of all items with the same key
        async def group(desired_key: Any, value: Any) -> AsyncIterator[Any]:
            nonlocal current_value, current_key, exhausted
            yield value
            async for value in async_iter:
                next_key: Any = await make_key(value)
                if next_key == desired_key:
                    yield value
                else:
                    exhausted = True
                    current_value = value
                    current_key = next_key
                    break

        try:
            while True:
                next_group = await seek_group()
                async with ScopedIter(next_group) as scoped_group:
                    yield current_key, scoped_group
        except StopAsyncIteration:
            return
