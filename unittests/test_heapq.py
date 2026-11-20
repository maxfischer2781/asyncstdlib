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


class MergeInterrupted(BaseException):
    pass


@pytest.fixture
def tracked_iterators():
    closed = set()

    async def make(name, values):
        try:
            for value in values:
                yield value
        finally:
            closed.add(name)

    return make, closed


@pytest.mark.parametrize("error_type", [RuntimeError, MergeInterrupted])
@sync
async def test_merge_closes_iterators_when_aiter_fails(tracked_iterators, error_type):
    make, closed = tracked_iterators

    class FailingIterable:
        def __aiter__(self):
            raise error_type("cannot create iterator")

    # Keep a reference so garbage collection cannot perform merge's cleanup.
    first = make("first", range(2))
    with pytest.raises(error_type, match="cannot create iterator"):
        await a.anext(a.merge(first, FailingIterable()))
    assert closed == {"first"}


@pytest.mark.parametrize("error_type", [RuntimeError, MergeInterrupted])
@sync
async def test_merge_closes_iterators_when_first_item_fails(
    tracked_iterators, error_type
):
    make, closed = tracked_iterators

    async def failing():
        try:
            raise error_type("cannot read first item")
            yield  # pragma: no cover
        finally:
            closed.add("second")

    iterators = [make("first", range(2)), failing()]
    with pytest.raises(error_type, match="cannot read first item"):
        await a.anext(a.merge(*iterators))
    assert closed == {"first", "second"}


@pytest.mark.parametrize("make_key", [lambda key: key, awaitify])
@pytest.mark.parametrize("error_type", [RuntimeError, MergeInterrupted])
@sync
async def test_merge_closes_iterators_when_initial_key_fails(
    tracked_iterators, make_key, error_type
):
    make, closed = tracked_iterators

    class UncreatedIterable:
        def __aiter__(self):
            raise AssertionError("the first key fails before this iterator is created")

    def key(value):
        raise error_type("cannot compute key")

    first = make("first", range(2))
    with pytest.raises(error_type, match="cannot compute key"):
        await a.anext(a.merge(first, UncreatedIterable(), key=make_key(key)))
    assert closed == {"first"}


@pytest.mark.parametrize("error_type", [RuntimeError, MergeInterrupted])
@sync
async def test_merge_closes_iterators_on_iteration_error(tracked_iterators, error_type):
    make, closed = tracked_iterators

    async def first():
        try:
            # This stream is selected first; its next item raises the error.
            yield 0
            raise error_type("cannot read next item")
        finally:
            closed.add("first")

    iterators = [first(), make("second", [1])]
    merged = a.merge(*iterators)
    await a.anext(merged)
    with pytest.raises(error_type, match="cannot read next item"):
        await a.anext(merged)
    assert closed == {"first", "second"}


@pytest.mark.parametrize("values", [[], [0]])
@sync
async def test_merge_closes_empty_and_exhausted_iterators(values):
    closed = set()

    # Unlike async generators, these iterators do not close themselves on exhaustion.
    class CloseableIterator:
        def __init__(self):
            self.values = iter(values)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self.values)
            except StopIteration:
                raise StopAsyncIteration from None

        async def aclose(self):
            closed.add("iterator")

    assert await a.list(a.merge(CloseableIterator(), [0])) == sorted(values + [0])
    assert closed == {"iterator"}


@sync
async def test_merge_closes_iterators_when_closed_early(tracked_iterators):
    make, closed = tracked_iterators
    iterators = [make("first", range(2)), make("second", range(2))]
    merged = a.merge(*iterators)
    await a.anext(merged)
    await merged.aclose()
    assert closed == {"first", "second"}


@pytest.mark.parametrize("error_type", [RuntimeError, MergeInterrupted])
@sync
async def test_merge_attempts_all_iterator_cleanup(tracked_iterators, error_type):
    make, closed = tracked_iterators

    async def second():
        try:
            yield 0
        finally:
            closed.add("second")
            raise error_type("cannot close second iterator")

    iterators = [make("first", range(2)), second(), make("third", range(2))]
    merged = a.merge(*iterators)
    await a.anext(merged)
    with pytest.raises(error_type, match="cannot close second iterator"):
        await merged.aclose()
    assert closed == {"first", "second", "third"}


@pytest.mark.parametrize(
    "first_error, second_error",
    [
        (KeyboardInterrupt("interrupted"), ValueError("close failed")),
        (ValueError("close failed"), KeyboardInterrupt("interrupted")),
    ],
)
@sync
async def test_merge_cleanup_preserves_interruption(
    tracked_iterators, first_error, second_error
):
    make, closed = tracked_iterators

    async def first():
        try:
            yield 0
        finally:
            closed.add("first")
            raise first_error

    async def second():
        try:
            yield 0
        finally:
            closed.add("second")
            raise second_error

    iterators = [first(), second(), make("third", range(2))]
    merged = a.merge(*iterators)
    await a.anext(merged)
    with pytest.raises(KeyboardInterrupt, match="interrupted"):
        await merged.aclose()
    assert closed == {"first", "second", "third"}


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, MergeInterrupted])
@sync
async def test_merge_cleanup_preserves_active_interruption(
    tracked_iterators, error_type
):
    make, closed = tracked_iterators
    interruption = error_type("interrupted")

    async def first():
        try:
            yield 0
            raise interruption
        finally:
            closed.add("first")

    async def second():
        try:
            yield 1
        finally:
            closed.add("second")
            raise ValueError("close failed")

    iterators = [first(), second(), make("third", [2])]
    merged = a.merge(*iterators)
    await a.anext(merged)
    with pytest.raises(error_type, match="interrupted") as caught:
        await a.anext(merged)
    assert caught.value is interruption
    assert closed == {"first", "second", "third"}


@sync
async def test_merge_cleanup_does_not_restore_callers_interruption():
    class FailingCloseIterator:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def aclose(self):
            raise ValueError("close failed")

    try:
        raise KeyboardInterrupt("already handled")
    except KeyboardInterrupt:
        with pytest.raises(ValueError, match="close failed"):
            await a.list(a.merge(FailingCloseIterator()))


@sync
async def test_merge_respects_scoped_iterator_ownership(tracked_iterators):
    make, closed = tracked_iterators
    async with a.scoped_iter(make("source", range(2))) as iterator:
        merged = a.merge(iterator)
        assert await a.anext(merged) == 0
        await merged.aclose()
        assert closed == set()
        assert await a.anext(iterator) == 1
    assert closed == {"source"}


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
