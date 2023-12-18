import itertools
import sys
import platform

import pytest

import asyncstdlib as a

from .utility import sync, asyncify, awaitify, multi_sync, Schedule, Switch, Lock


@sync
async def test_accumulate():
    async def reduction(x, y):
        return x + y

    for reducer in (reduction, lambda x, y: x + y):
        for itertype in (asyncify, list):
            assert await a.list(a.accumulate(itertype([0, 1]), reducer)) == list(
                itertools.accumulate([0, 1], lambda x, y: x + y)
            )
            assert await a.list(
                a.accumulate(itertype([0, 1, 2, 3, 4, 0, -5]), reducer)
            ) == list(itertools.accumulate([0, 1, 2, 3, 4, 0, -5], lambda x, y: x + y))
            assert await a.list(a.accumulate(itertype([12]), reducer)) == list(
                itertools.accumulate([12], lambda x, y: x + y)
            )
            assert await a.list(a.accumulate(itertype([1]), reducer, initial=23)) == [
                23,
                24,
            ]
            assert await a.list(a.accumulate(itertype([]), reducer, initial=42)) == [42]


@sync
async def test_accumulate_default():
    for itertype in (asyncify, list):
        assert await a.list(a.accumulate(itertype([0, 1]))) == list(
            itertools.accumulate([0, 1])
        )
        assert await a.list(a.accumulate(itertype([0, 1, 2, 3, 4, 0, -5]))) == list(
            itertools.accumulate([0, 1, 2, 3, 4, 0, -5])
        )
        assert await a.list(a.accumulate(itertype([12]))) == list(
            itertools.accumulate([12])
        )
        assert await a.list(a.accumulate(itertype([1]), initial=23)) == [
            23,
            24,
        ]
        assert await a.list(a.accumulate(itertype([]), initial=42)) == [42]


@sync
async def test_accumulate_misuse():
    with pytest.raises(TypeError):
        assert await a.list(a.accumulate([]))


batched_cases = [
    (range(10), 2, [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]),
    (range(10), 3, [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9,)]),
    (range(10), 17, [tuple(range(10))]),
    ([], 2, []),
]


@pytest.mark.parametrize("iterable, length, result", batched_cases)
@sync
async def test_batched(iterable, length, result):
    assert await a.list(a.batched(iterable, length)) == result
    assert await a.list(a.batched(asyncify(iterable), length)) == result


@sync
@pytest.mark.parametrize("length", (0, -1))
async def test_batched_invalid(length):
    with pytest.raises(ValueError):
        await a.list(a.batched(range(10), length))


@sync
async def test_cycle():
    async for _ in a.cycle([]):
        assert False
    assert True
    async for idx, val in a.enumerate(a.cycle([0, 1])):
        assert idx % 2 == val
        if idx == 6:
            break
    assert idx == 6


chains = [
    ([0, 1, 2, 3], [4, 5, 6, 7]),
    ([4], [3], [2], [1]),
    ([], [], [], [1], [], []),
]


@pytest.mark.parametrize("iterables", chains)
@sync
async def test_chain(iterables):
    for itertype in (asyncify, list):
        assert await a.list(a.chain(*map(itertype, iterables))) == list(
            itertools.chain(*iterables)
        )
        assert await a.list(a.chain.from_iterable(map(itertype, iterables))) == list(
            itertools.chain.from_iterable(iterables)
        )


class ACloseFacade:
    """Wrapper to check if an iterator has been closed"""

    def __init__(self, iterable):
        self.closed = False
        self.__wrapped__ = iterable
        self._iterator = a.iter(iterable)

    async def __anext__(self):
        if self.closed:
            raise StopAsyncIteration()
        return await self._iterator.__anext__()

    def __aiter__(self):
        return self

    async def aclose(self):
        if hasattr(self._iterator, "aclose"):
            await self._iterator.aclose()
        self.closed = True


@pytest.mark.parametrize("iterables", chains)
@sync
async def test_chain_close_auto(iterables):
    """Test that `chain` closes exhausted iterators"""
    closeable_iterables = [ACloseFacade(iterable) for iterable in iterables]
    assert await a.list(a.chain(*closeable_iterables)) == list(
        itertools.chain(*iterables)
    )
    assert all(iterable.closed for iterable in closeable_iterables)


# insert a known filled iterable since chain closes all that are exhausted
@pytest.mark.parametrize("iterables", [([1], *chain) for chain in chains])
@pytest.mark.parametrize(
    "chain_type, must_close",
    [(lambda iterators: a.chain(*iterators), True), (a.chain.from_iterable, False)],
)
@sync
async def test_chain_close_partial(iterables, chain_type, must_close):
    """Test that `chain` closes owned iterators"""
    closeable_iterables = [ACloseFacade(iterable) for iterable in iterables]
    chain = chain_type(closeable_iterables)
    assert await a.anext(chain) == next(itertools.chain(*iterables))
    await chain.aclose()
    assert all(iterable.closed == must_close for iterable in closeable_iterables[1:])
    # closed chain must remain closed regardless of iterators
    assert await a.anext(chain, "sentinel") == "sentinel"


compress_cases = [
    (range(20), [idx % 2 for idx in range(20)]),
    ([1] * 5, [True, True, False, True, True]),
    ([1] * 128, [False]),
    ([], []),
]


@pytest.mark.parametrize("data, selectors", compress_cases)
@sync
async def test_compress(data, selectors):
    expected = list(itertools.compress(data, selectors))
    assert await a.list(a.compress(data, selectors)) == expected
    assert await a.list(a.compress(asyncify(data), selectors)) == expected
    assert await a.list(a.compress(data, asyncify(selectors))) == expected
    assert await a.list(a.compress(asyncify(data), asyncify(selectors))) == expected


droptakewhile_cases = [
    (range(20), lambda x: x < 5),
    (range(20), lambda x: x > 5),
    ([1] * 12, lambda x: x > 5),
    ([1, 2, 3, 4] * 4, lambda x: x < 3),
    ([1, 2, 3, 4] * 4, lambda x: True),
    ([1, 2, 3, 4] * 4, lambda x: False),
]


@pytest.mark.parametrize("iterable, predicate", droptakewhile_cases)
@sync
async def test_dropwhile(iterable, predicate):
    expected = list(itertools.dropwhile(predicate, iterable))
    assert await a.list(a.dropwhile(predicate, iterable)) == expected
    assert await a.list(a.dropwhile(awaitify(predicate), iterable)) == expected
    assert await a.list(a.dropwhile(predicate, asyncify(iterable))) == expected
    assert (
        await a.list(a.dropwhile(awaitify(predicate), asyncify(iterable))) == expected
    )


filterfalse_cases = (
    (lambda x: True, [0, 1] * 5),
    (lambda x: False, [0, 1] * 5),
    (lambda x: x, [0, 1] * 5),
    (lambda x: x < 5, range(20)),
    (lambda x: x > 5, range(20)),
)


@pytest.mark.parametrize("predicate, iterable", filterfalse_cases)
@sync
async def test_filterfalse(predicate, iterable):
    expected = list(itertools.filterfalse(predicate, iterable))
    assert await a.list(a.filterfalse(predicate, iterable)) == expected
    assert await a.list(a.filterfalse(awaitify(predicate), iterable)) == expected
    assert await a.list(a.filterfalse(predicate, asyncify(iterable))) == expected
    assert (
        await a.list(a.filterfalse(awaitify(predicate), asyncify(iterable))) == expected
    )


@pytest.mark.parametrize("predicate, iterable", filterfalse_cases)
@sync
async def test_filterfalse_predicate_none(predicate, iterable):
    expected = list(itertools.filterfalse(None, iterable))
    assert await a.list(a.filterfalse(None, iterable)) == expected
    assert await a.list(a.filterfalse(None, asyncify(iterable))) == expected


@pytest.mark.parametrize("iterable, predicate", droptakewhile_cases)
@sync
async def test_takewhile(iterable, predicate):
    expected = list(itertools.takewhile(predicate, iterable))
    assert await a.list(a.takewhile(predicate, iterable)) == expected
    assert await a.list(a.takewhile(awaitify(predicate), iterable)) == expected
    assert await a.list(a.takewhile(predicate, asyncify(iterable))) == expected
    assert (
        await a.list(a.takewhile(awaitify(predicate), asyncify(iterable))) == expected
    )


@pytest.mark.parametrize("iterable", ((), (1, 2, 3, 4), range(25), range(500)))
@pytest.mark.parametrize(
    "slicing",
    ((None, None, None), (0,), (5,), (0, 20, 3), (5, 0, 1), (3, 50, 4), (5, None, 6)),
)
@sync
async def test_islice(iterable, slicing):
    expected = list(itertools.islice(iterable, *slicing))
    assert await a.list(a.islice(iterable, *slicing)) == expected
    assert await a.list(a.islice(asyncify(iterable), *slicing)) == expected


async def ayield_exactly(count: int):
    for item in range(count):
        yield item
    assert False, "Too many `anext` items requested"


@sync
@pytest.mark.parametrize("slicing", ((0,), (5,), (0, 20, 3), (5, 0, 1), (3, 50, 4)))
async def test_islice_exact(slicing):
    """`isclice` consumes exactly as many items as needed"""
    boundary = slice(*slicing) if len(slicing) > 1 else slice(0, slicing[0])
    expected = list(range(boundary.stop)[boundary])
    assert (
        await a.list(
            a.islice(ayield_exactly(max(boundary.start, boundary.stop)), *slicing)
        )
        == expected
    )


@sync
async def test_islice_scoped_iter():
    """multiple `isclice` on borrowed iterator are consecutive"""
    async_iterable, iterable = asyncify(range(10)), iter(range(10))
    async with a.scoped_iter(async_iterable) as a1:
        assert await a.list(a.islice(a1, 5)) == list(itertools.islice(iterable, 5))
        assert await a.list(a.islice(a1, 5)) == list(itertools.islice(iterable, 5))
        assert await a.list(a.islice(a1, 5)) == list(itertools.islice(iterable, 5))


starmap_cases = [
    (lambda x, y: x + y, [(1, 2), (3, 4)]),
    (lambda *args: sum(args), [range(i) for i in range(1, 10)]),
]


@pytest.mark.parametrize("function, iterable", starmap_cases)
@sync
async def test_starmap(function, iterable):
    expected = list(itertools.starmap(function, iterable))
    assert await a.list(a.starmap(function, iterable)) == expected
    assert await a.list(a.starmap(awaitify(function), iterable)) == expected
    assert await a.list(a.starmap(function, asyncify(iterable))) == expected
    assert await a.list(a.starmap(awaitify(function), asyncify(iterable))) == expected


@sync
async def test_tee():
    iterable = [1, 2, 3, -5, 12, 78, -1, 111]
    async with a.tee(iterable, n=3) as iterators:
        assert len(iterators) == 3
        for idx, iterator in enumerate(iterators):
            assert iterators[idx] == iterator
        for iterator in (iterators[1], iterators[0], iterators[2]):
            assert await a.list(iterator) == iterable
    async with a.tee(asyncify(iterable), n=3) as iterators:
        for iterator in iterators:
            assert await a.list(iterator) == iterable


@multi_sync
async def test_tee_concurrent_locked():
    """Test that properly uses a lock for synchronisation"""
    items = [1, 2, 3, -5, 12, 78, -1, 111]

    async def iter_values():
        for item in items:
            # switch to other tasks a few times to guarantees another runs
            for _ in range(5):
                await Switch()
            yield item

    async def test_peer(peer_tee):
        assert await a.list(peer_tee) == items

    head_peer, *peers = a.tee(iter_values(), n=len(items) // 2, lock=Lock())
    await Schedule(*map(test_peer, peers))
    await Switch()
    results = [item async for item in head_peer]
    assert results == items


# see https://github.com/python/cpython/issues/74956
@pytest.mark.skipif(
    sys.version_info < (3, 8),
    reason="async generators only protect against concurrent access since 3.8",
)
@pytest.mark.skipif(
    platform.python_implementation() != "CPython",
    reason="async generators only protect against concurrent access on CPython",
)
@multi_sync
async def test_tee_concurrent_unlocked():
    """Test that tee does not prevent concurrency without a lock"""
    items = list(range(12))

    # concurrency-unsafe iterator that task-switches between yields
    async def iter_values():
        for item in items:
            # switch to other tasks a few times to guarantee another runs
            for _ in range(5):
                await Switch()
            yield item

    async def test_peer(peer_tee):
        assert await a.list(peer_tee) == items

    # schedule two tasks that read via tee from the same iterator
    this, peer = a.tee(iter_values(), n=2)
    await Schedule(test_peer(peer))
    await Switch()
    # underlying generator raises RuntimeError when `__anext__` is interleaved
    with pytest.raises(RuntimeError):
        await test_peer(this)


@sync
async def test_pairwise():
    assert await a.list(a.pairwise(range(5))) == [(0, 1), (1, 2), (2, 3), (3, 4)]
    assert await a.list(a.pairwise(range(2))) == [(0, 1)]
    assert await a.list(a.pairwise(range(1))) == []
    assert await a.list(a.pairwise(range(0))) == []
    for count in range(5):
        assert await a.list(a.pairwise([0] * count)) == [(0, 0)] * (count - 1)


@sync
async def test_zip_longest():
    async for va, vb in a.zip_longest(asyncify(range(5)), range(5)):
        assert va == vb
    async for idx, vs in a.enumerate(a.zip_longest(asyncify(range(5)), range(5), [])):
        assert vs[0] == vs[1] == idx
        assert vs[2] is None
    async for _ in a.zip_longest():
        assert False


groupby_cases = [
    [0, 1, 1, 2, 2, 2, 3, 2],
    list(range(15)) + list(range(15)) + list(range(15)),
    [num for num in range(5) for _ in range(5)],
    [num for num in range(5) for _ in range(num)],
    [1, 1, 2, 2, 2, 2, 3, 3, 1, 2, 5, 5, 2, 2],
]


def identity(x):
    return x


def modulo(x):
    return x % 3


def divide(x):
    return x // 3


async def keys(gby):
    return [k async for k, _ in a.iter(gby)]


async def values(gby):
    return [await a.list(g) async for _, g in a.iter(gby)]


@pytest.mark.parametrize("iterable", groupby_cases)
@pytest.mark.parametrize("key", [identity, modulo, divide])
@pytest.mark.parametrize("view", [keys, values])
@sync
async def test_groupby(iterable, key, view):
    for akey in (key, awaitify(key)):
        assert await view(a.groupby(iterable)) == await view(
            itertools.groupby(iterable)
        )
        assert await view(a.groupby(asyncify(iterable))) == await view(
            itertools.groupby(iterable)
        )
        assert await view(a.groupby(iterable, key=akey)) == await view(
            itertools.groupby(iterable, key=key)
        )
        assert await view(a.groupby(asyncify(iterable), key=akey)) == await view(
            itertools.groupby(iterable, key=key)
        )
