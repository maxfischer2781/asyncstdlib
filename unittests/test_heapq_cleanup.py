"""Resource ownership of the iterators created by merge."""

import asyncio

import pytest

import asyncstdlib as a

from .utility import sync


class OwnedIterator:
    def __init__(self, values, head_error=None, close_error=None):
        self.values = iter(values)
        self.head_error = head_error
        self.close_error = close_error
        self.closed = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.head_error is not None:
            raise self.head_error
        try:
            return next(self.values)
        except StopIteration:
            raise StopAsyncIteration from None

    async def aclose(self):
        self.closed += 1
        if self.close_error is not None:
            raise self.close_error


class OwnedSource:
    def __init__(self, values, iter_error=None, head_error=None, close_error=None):
        self.values = values
        self.iter_error = iter_error
        self.head_error = head_error
        self.close_error = close_error
        self.created = []

    def __aiter__(self):
        if self.iter_error is not None:
            raise self.iter_error
        iterator = OwnedIterator(self.values, self.head_error, self.close_error)
        self.created.append(iterator)
        return iterator


@pytest.mark.parametrize("failure", ["iter", "head", "key", "async_key", "cancel"])
@sync
async def test_merge_closes_created_iterators_when_initialization_fails(failure):
    error = (
        asyncio.CancelledError() if failure == "cancel" else RuntimeError("init failed")
    )
    first = OwnedSource([1, 3])
    second = OwnedSource(
        [2, 4],
        iter_error=error if failure == "iter" else None,
        head_error=error if failure in ("head", "cancel") else None,
    )
    unstarted = OwnedSource([5])

    def key(value):
        if failure in ("key", "async_key") and value == 2:
            raise error
        return value

    async def async_key(value):
        return key(value)

    merged = a.merge(
        first, second, unstarted, key=async_key if failure == "async_key" else key
    )
    with pytest.raises(type(error)):
        await a.anext(merged)
    await merged.aclose()
    assert len(first.created) == 1
    assert len(second.created) == int(failure != "iter")
    assert unstarted.created == []
    assert all(
        iterator.closed == 1
        for source in (first, second)
        for iterator in source.created
    )


@sync
async def test_merge_closes_exhausted_and_empty_created_iterators():
    sources = [OwnedSource([]), OwnedSource([1]), OwnedSource([2, 3])]
    assert await a.list(a.merge(*sources)) == [1, 2, 3]
    assert all(len(source.created) == 1 for source in sources)
    assert all(source.created[0].closed == 1 for source in sources)


@sync
async def test_merge_closes_created_iterators_when_closed_early():
    sources = [OwnedSource([]), OwnedSource([1, 3]), OwnedSource([2, 4])]
    merged = a.merge(*sources)
    assert await a.anext(merged) == 1
    await merged.aclose()
    assert all(source.created[0].closed == 1 for source in sources)


@sync
async def test_merge_attempts_all_created_iterator_cleanup():
    sources = [
        OwnedSource([1]),
        OwnedSource([2], close_error=RuntimeError("close failed")),
        OwnedSource([3]),
    ]
    merged = a.merge(*sources)
    assert await a.anext(merged) == 1
    with pytest.raises(RuntimeError, match="close failed"):
        await merged.aclose()
    assert all(source.created[0].closed == 1 for source in sources)


@sync
async def test_merge_respects_scoped_iterator_ownership():
    source = OwnedSource([1, 2, 3])
    async with a.scoped_iter(source) as iterator:
        merged = a.merge(iterator)
        assert await a.anext(merged) == 1
        await merged.aclose()
        assert source.created[0].closed == 0
        assert await a.anext(iterator) == 2
    assert source.created[0].closed == 1
