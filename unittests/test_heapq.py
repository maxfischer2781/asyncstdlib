import heapq

import platform
import pytest
import random

import asyncstdlib as a

from .utility import sync, asyncify, awaitify

MERGE_SAMPLES: "list[list[list[float]]]" = [
    # pre-sorted
    [[1, 2], [3, 4]],
    [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
    # ragged and shuffled
    [[1, 4, 7], [2, 5, 8], [3, 6, 9]],
    [[1], [2, 3], [4, 5, 6], [7, 8, 9]],
    [[1], [2, 4, 6], [3], [5, 7, 8, 9]],
    # duplication
    [[1, 2], [1, 2]],
    [[1, 2, 3, 4] for _ in range(3)],
    [[-4, -3, -2, 1, 2, 3, 4] for _ in range(3)],
    # random input
    [sorted(random.random() for _ in range(5)) for _ in range(5)],
    # degenerate cases
    [[], []],
    [[]],
]


@pytest.mark.parametrize("samples", MERGE_SAMPLES)
@pytest.mark.parametrize("reverse", [False, True])
@sync
async def test_merge_stdlib(samples: "list[list[float]]", reverse: bool) -> None:
    """Compare `heapq.merge` against stdlib implementation"""
    samples = samples if not reverse else [sample[::-1] for sample in samples]
    assert list(heapq.merge(*samples, reverse=reverse)) == [
        item async for item in a.merge(*map(asyncify, samples), reverse=reverse)
    ]


@pytest.mark.parametrize("samples", MERGE_SAMPLES)
@pytest.mark.parametrize("reverse", [False, True])
@sync
async def test_merge_stdlib_key(samples: "list[list[float]]", reverse: bool) -> None:
    """Compare `heapq.merge` with key against stdlib implementation"""
    # use a key that reverses the result => must reverse input
    samples = samples if reverse else [sample[::-1] for sample in samples]
    assert list(heapq.merge(*samples, key=lambda x: -x, reverse=reverse)) == [
        item
        async for item in a.merge(
            *map(asyncify, samples), key=awaitify(lambda x: -x), reverse=reverse
        )
    ]


@sync
async def test_merge_closes_iterators_when_aiter_fails():
    closed = []

    async def first():
        try:
            yield 1
            yield 3
        finally:
            closed.append("first")

    class FailingIterable:
        def __aiter__(self):
            raise RuntimeError("cannot create iterator")

    # Retain the iterator so garbage collection cannot perform merge's cleanup.
    iterator = first()
    with pytest.raises(RuntimeError, match="cannot create iterator"):
        await a.anext(a.merge(iterator, FailingIterable()))
    assert closed == ["first"]


@sync
async def test_merge_closes_iterators_when_first_item_fails():
    closed = []

    async def first():
        try:
            yield 1
            yield 3
        finally:
            closed.append("first")

    async def failing():
        try:
            raise RuntimeError("cannot read first item")
            yield 2
        finally:
            closed.append("failing")

    iterators = [first(), failing()]
    with pytest.raises(RuntimeError, match="cannot read first item"):
        await a.anext(a.merge(*iterators))
    assert closed == ["failing", "first"]


@pytest.mark.parametrize("make_key", [lambda key: key, awaitify])
@sync
async def test_merge_closes_iterators_when_initial_key_fails(make_key):
    closed = []
    started = []

    async def first():
        try:
            yield 1
            yield 3
        finally:
            closed.append("first")

    async def second():
        try:
            yield 2
            yield 4
        finally:
            closed.append("second")

    async def later():
        started.append("later")
        yield 5

    def key(value):
        # The first iterator is initialized before the second key fails.
        if value == 2:
            raise RuntimeError("cannot compute key")
        return value

    iterators = [first(), second(), later()]
    with pytest.raises(RuntimeError, match="cannot compute key"):
        await a.anext(a.merge(*iterators, key=make_key(key)))
    assert closed == ["second", "first"]
    assert started == []


@sync
async def test_merge_closes_iterators_on_base_exception():
    class Interrupted(BaseException):
        pass

    closed = []

    async def first():
        try:
            yield 1
            raise Interrupted
        finally:
            closed.append("first")

    async def second():
        try:
            yield 2
            yield 4
        finally:
            closed.append("second")

    iterators = [first(), second()]
    merged = a.merge(*iterators)
    assert await a.anext(merged) == 1
    with pytest.raises(Interrupted):
        await a.anext(merged)
    assert closed == ["first", "second"]


@sync
async def test_merge_closes_empty_and_exhausted_iterators():
    closed = []

    class EmptyIterator:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def aclose(self):
            closed.append("empty")

    class SingleItemIterator:
        def __init__(self):
            self.values = iter([1])

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self.values)
            except StopIteration:
                raise StopAsyncIteration from None

        async def aclose(self):
            closed.append("single")

    assert await a.list(a.merge(EmptyIterator(), SingleItemIterator(), [2, 3])) == [
        1,
        2,
        3,
    ]
    assert closed == ["single", "empty"]


@sync
async def test_merge_closes_iterators_when_closed_early():
    closed = []

    async def first():
        try:
            yield 1
            yield 3
        finally:
            closed.append("first")

    async def second():
        try:
            yield 2
            yield 4
        finally:
            closed.append("second")

    iterators = [first(), second()]
    merged = a.merge(*iterators)
    assert await a.anext(merged) == 1
    await merged.aclose()
    assert closed == ["second", "first"]


@sync
async def test_merge_attempts_all_iterator_cleanup():
    closed = []

    async def first():
        try:
            yield 1
            yield 4
        finally:
            closed.append("first")

    async def second():
        try:
            yield 2
            yield 5
        finally:
            closed.append("second")
            raise RuntimeError("cannot close second iterator")

    async def third():
        try:
            yield 3
            yield 6
        finally:
            closed.append("third")

    iterators = [first(), second(), third()]
    merged = a.merge(*iterators)
    assert await a.anext(merged) == 1
    with pytest.raises(RuntimeError, match="cannot close second iterator"):
        await merged.aclose()
    assert closed == ["third", "second", "first"]


@sync
async def test_merge_respects_scoped_iterator_ownership():
    closed = []

    async def source():
        try:
            yield 1
            yield 2
        finally:
            closed.append("source")

    async with a.scoped_iter(source()) as iterator:
        merged = a.merge(iterator)
        assert await a.anext(merged) == 1
        await merged.aclose()
        assert closed == []
        assert await a.anext(iterator) == 2
    assert closed == ["source"]


PAIR_MERGE_SAMPLES: "list[list[list[tuple[float, int | str]]]]" = [
    [[(1, "first"), (2, "first")], [(1, "second"), (2, "second")]],
    [[(0, "first"), (1, "first")], [(1, "second"), (2, "second")]],
    [[(1, "first"), (2, "first")], [(0, "second"), (1, "second")]],
    [[(val, idx) for val in range(5)] for idx in range(3)],
    [[(val - idx, idx) for val in range(5)] for idx in range(3)],
    [[(val + idx, idx) for val in range(5)] for idx in range(3)],
]


@pytest.mark.parametrize("samples", PAIR_MERGE_SAMPLES)
@pytest.mark.parametrize("reverse", [False, True])
@sync
async def test_merge_stdlib_pairs(
    samples: "list[list[tuple[float, int]]]", reverse: bool
) -> None:
    """Compare `heapq.merge` with (key, tag) pairs against stdlib implementation"""

    def key(pair: "tuple[float, int]") -> float:
        return pair[0]

    samples = samples if not reverse else [sample[::-1] for sample in samples]
    assert list(heapq.merge(*samples, key=key, reverse=reverse)) == await a.list(
        a.merge(*map(asyncify, samples), key=awaitify(key), reverse=reverse)
    )


# Technically, merge requires pre-sorted input which excludes unorder'able items
# Practically, `float` includes `nan` and data includes `float`
NAN_MERGE_SAMPLES: "list[list[list[float]]]" = [
    [[1, 2, float("nan")], [1, 2, float("nan")]],
    [[1, float("nan"), 2], [1, float("nan"), 2]],
    [[float("nan"), 1, 2], [float("nan"), 1, 2]],
]


@pytest.mark.skipif(
    platform.python_implementation() != "CPython",
    reason="heapq.merge for unordered items is specific to CPython",
)
@pytest.mark.parametrize("samples", NAN_MERGE_SAMPLES)
@pytest.mark.parametrize("reverse", [False, True])
@sync
async def test_merge_unordered(samples: "list[list[float]]", reverse: bool) -> None:
    r"""Compare `heapq.merge` against stdlib implementation given `nan`\ s"""
    samples = samples if not reverse else [sample[::-1] for sample in samples]
    assert pytest.approx(list(heapq.merge(*samples, reverse=reverse)), nan_ok=True) == [
        item async for item in a.merge(*map(asyncify, samples), reverse=reverse)
    ]


MINMAX_SAMPLES = [
    [0, 3, 1, 4, 2, 5],
    [0, -3, 1, -4, -2, 5],
    # [i * 1.1 for i in range(20)],
    # [random.randint(-5, 5) in range(20)],
    # [i * i if i % 3 else -i * i for i in range(2000)],
]


@pytest.mark.parametrize("sample", MINMAX_SAMPLES)
@pytest.mark.parametrize("n", [0, 1, 2, 10, 100, 400, 999, 1000, 1100])
@sync
async def test_nsmallest_stdlib(sample, n):
    assert heapq.nsmallest(n, sample) == await a.nsmallest(asyncify(sample), n)


@pytest.mark.parametrize("sample", MINMAX_SAMPLES)
@pytest.mark.parametrize("n", [0, 1, 2, 10, 100, 400, 999, 1000, 1100])
@sync
async def test_nlargest_stdlib(sample, n):
    assert heapq.nlargest(n, sample) == await a.nlargest(asyncify(sample), n)


@pytest.mark.parametrize("sample", MINMAX_SAMPLES)
@pytest.mark.parametrize("n", [0, 1, 2, 10, 100, 400, 999, 1000, 1100])
@sync
async def test_nsmallest_stdlib_key(sample, n):
    assert heapq.nsmallest(n, sample, key=lambda x: -x) == await a.nsmallest(
        asyncify(sample), n, key=lambda x: -x
    )


@pytest.mark.parametrize("sample", MINMAX_SAMPLES)
@pytest.mark.parametrize("n", [0, 1, 2, 10, 100, 400, 999, 1000, 1100])
@sync
async def test_nlargest_stdlib_key(sample, n):
    assert heapq.nlargest(n, sample, key=lambda x: -x) == await a.nlargest(
        asyncify(sample), n, key=lambda x: -x
    )
