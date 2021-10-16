import itertools

import pytest

import asyncstdlib as a

from .utility import sync, asyncify, awaitify


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
