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


PAIR_MERGE_SAMPLES: "list[list[list[tuple[float, int]]]]" = [
    [[(val, idx) for val in range(5)] for idx in range(3)],
]


@pytest.mark.parametrize("samples", PAIR_MERGE_SAMPLES)
@pytest.mark.parametrize("reverse", [False, True])
@sync
async def test_merge_stdlib_pairs(
    samples: "list[list[tuple[float, int]]]", reverse: bool
) -> None:
    """Compare `heapq.merge` with key against stdlib implementation"""

    def key(pair: "tuple[float, int]") -> float:
        return pair[0]

    samples = samples if not reverse else [sample[::-1] for sample in samples]
    assert list(heapq.merge(*samples, key=key, reverse=reverse)) == [
        item
        async for item in a.merge(
            *map(asyncify, samples), key=awaitify(key), reverse=reverse
        )
    ]


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
