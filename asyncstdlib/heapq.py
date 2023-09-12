from typing import (
    Generic,
    AsyncIterator,
    Tuple,
    List,
    Optional,
    Callable,
    Any,
    overload,
    Awaitable,
)
import heapq as _heapq

from .builtins import enumerate as a_enumerate, zip as a_zip
from ._core import aiter, awaitify, ScopedIter, borrow
from ._typing import AnyIterable, LT, T, SupportsLT


class _KeyIter(Generic[LT]):
    __slots__ = ("head", "tail", "reverse", "head_key", "key")

    @overload
    def __init__(
        self,
        head: T,
        tail: AsyncIterator[T],
        reverse: bool,
        head_key: LT,
        key: Callable[[T], Awaitable[LT]],
    ):
        pass

    @overload
    def __init__(
        self, head: LT, tail: AsyncIterator[LT], reverse: bool, head_key: LT, key: None
    ):
        pass

    def __init__(
        self,
        head: Any,
        tail: AsyncIterator[Any],
        reverse: bool,
        head_key: LT,
        key: Any,
    ):
        self.head = head
        self.head_key = head_key
        self.tail = tail
        self.key = key
        self.reverse = reverse

    @overload
    @classmethod
    def from_iters(
        cls,
        iterables: Tuple[AnyIterable[T], ...],
        reverse: bool,
        key: Callable[[T], Awaitable[LT]],
    ) -> "AsyncIterator[_KeyIter[LT]]":
        pass

    @overload
    @classmethod
    def from_iters(
        cls, iterables: Tuple[AnyIterable[LT], ...], reverse: bool, key: None
    ) -> "AsyncIterator[_KeyIter[LT]]":
        pass

    @classmethod
    async def from_iters(
        cls,
        iterables: Tuple[AnyIterable[Any], ...],
        reverse: bool,
        key: Optional[Callable[[Any], Any]],
    ) -> "AsyncIterator[_KeyIter[Any]]":
        for iterable in iterables:
            iterator = aiter(iterable)
            try:
                head = await iterator.__anext__()
            except StopAsyncIteration:
                pass
            else:
                head_key = await key(head) if key is not None else head
                yield cls(head, iterator, reverse, head_key, key)

    async def pull_head(self) -> bool:
        """
        Pull the next ``head`` element from the iterator and signal success
        """
        try:
            self.head = head = await self.tail.__anext__()
        except StopAsyncIteration:
            return False
        else:
            self.head_key = await self.key(head) if self.key is not None else head
            return True

    def __lt__(self, other: "_KeyIter[LT]") -> bool:
        return self.reverse ^ (self.head_key < other.head_key)

    def __eq__(self, other: "_KeyIter[LT]") -> bool:  # type: ignore[override]
        return not (self.head_key < other.head_key or other.head_key < self.head_key)


@overload
def merge(
    *iterables: AnyIterable[LT], key: None = ..., reverse: bool = ...
) -> AsyncIterator[LT]:
    pass


@overload
def merge(
    *iterables: AnyIterable[T],
    key: Callable[[T], Awaitable[LT]] = ...,
    reverse: bool = ...,
) -> AsyncIterator[T]:
    pass


@overload
def merge(
    *iterables: AnyIterable[T], key: Callable[[T], LT] = ..., reverse: bool = ...
) -> AsyncIterator[T]:
    pass


async def merge(
    *iterables: AnyIterable[Any],
    key: Optional[Callable[[Any], Any]] = None,
    reverse: bool = False,
) -> AsyncIterator[Any]:
    """
    Merge all pre-sorted (async) ``iterables`` into a single sorted iterator

    This works similar to ``sorted(chain(*iterables), key=key, reverse=reverse)`` but
    operates lazily: at any moment only one item of each iterable is stored for the
    comparison. This allows merging streams of pre-sorted items, such as timestamped
    records from multiple sources.

    The optional ``key`` argument specifies a one-argument (async) callable, which
    provides a substitute for determining the sort order of each item.
    The special value and default :py:data:`None` represents the identity function,
    comparing items directly.

    The default sort order is ascending, that is items with ``a < b`` imply ``a``
    is yielded before ``b``. Use ``reverse=True`` for descending sort order.
    The ``iterables`` must be pre-sorted in the same order.
    """
    a_key = awaitify(key) if key is not None else None
    # sortable iterators with (reverse) position to ensure stable sort for ties
    iter_heap: List[Tuple[_KeyIter[Any], int]] = [
        (itr, idx if not reverse else -idx)
        async for idx, itr in a_enumerate(
            _KeyIter.from_iters(iterables, reverse, a_key)
        )
    ]
    try:
        _heapq.heapify(iter_heap)
        # there are at least two iterators that need merging
        while len(iter_heap) > 1:
            while True:
                itr, idx = iter_heap[0]
                yield itr.head
                if await itr.pull_head():
                    _heapq.heapreplace(iter_heap, (itr, idx))
                else:
                    _heapq.heappop(iter_heap)
                    break
        # there is only one iterator left, no need for merging
        if iter_heap:
            itr, idx = iter_heap[0]
            yield itr.head
            async for item in itr.tail:
                yield item
    finally:
        for itr, _ in iter_heap:
            if hasattr(itr.tail, "aclose"):
                await itr.tail.aclose()


class ReverseLT(Generic[LT]):
    """Helper to reverse ``a < b`` ordering"""

    __slots__ = ("key",)

    def __init__(self, key: LT):
        self.key = key

    def __lt__(self, other: "ReverseLT[LT]") -> bool:
        return other.key < self.key


# Python's heapq provides a *min*-heap
# When finding the n largest items, heapq tracks the *minimum* item still large enough.
# In other words, during search we maintain opposite sort order than what is requested.
# We turn the min-heap into a max-sort in the end.
async def _largest(
    iterable: AsyncIterator[T],
    n: int,
    key: Callable[[T], Awaitable[LT]],
    reverse: bool,
) -> List[T]:
    ordered: Callable[[SupportsLT], SupportsLT] = (
        ReverseLT if reverse else lambda x: x  # type: ignore
    )
    async with ScopedIter(iterable) as iterator:
        # assign an ordering to items to solve ties
        order_sign = -1 if reverse else 1
        n_heap = [
            (ordered(await key(item)), index * order_sign, item)
            async for index, item in a_zip(range(n), borrow(iterator))
        ]
        if not n_heap:
            return []
        _heapq.heapify(n_heap)
        worst_key = n_heap[0][0]
        next_index = n * order_sign
        async for item in iterator:
            item_key = ordered(await key(item))
            if worst_key < item_key:
                _heapq.heapreplace(n_heap, (item_key, next_index, item))
                worst_key = n_heap[0][0]
                next_index += 1 * order_sign
        n_heap.sort(reverse=True)
    return [item for _, _, item in n_heap]


async def _identity(x: T) -> T:
    return x


async def nlargest(
    iterable: AsyncIterator[T],
    n: int,
    key: Optional[Callable[[Any], Awaitable[Any]]] = None,
) -> List[T]:
    """
    Return a sorted list of the ``n`` largest elements from the (async) iterable

    The optional ``key`` argument specifies a one-argument (async) callable, which
    provides a substitute for determining the sort order of each item.
    The special value and default :py:data:`None` represents the identity functions,
    comparing items directly.

    The result is equivalent to ``sorted(iterable, key=key, reverse=True)[:n]``,
    but ``iterable`` is consumed lazily and items are discarded eagerly.
    """
    a_key: Callable[[Any], Awaitable[Any]] = (
        awaitify(key) if key is not None else _identity  # type: ignore
    )
    return await _largest(iterable=iterable, n=n, key=a_key, reverse=False)


async def nsmallest(
    iterable: AsyncIterator[T],
    n: int,
    key: Optional[Callable[[Any], Awaitable[Any]]] = None,
) -> List[T]:
    """
    Return a sorted list of the ``n`` smallest elements from the (async) iterable

    Provides the reverse functionality to :py:func:`~.nlargest`.
    """
    a_key: Callable[[Any], Awaitable[Any]] = (
        awaitify(key) if key is not None else _identity  # type: ignore
    )
    return await _largest(iterable=iterable, n=n, key=a_key, reverse=True)
