from typing import AsyncIterator
from asyncstdlib import itertools
from typing_extensions import assert_type


async def test_cycle() -> None:
    async for x in itertools.cycle([1]):
        assert_type(x, int)


async def test_accumulate() -> None:
    async for x in itertools.accumulate([1]):
        assert_type(x, int)


async def test_batched() -> None:
    async for x in itertools.batched([1], 1):
        assert_type(x, "tuple[int]")


async def test_chain() -> None:
    async for x in itertools.chain([1]):
        assert_type(x, int)


async def test_compress() -> None:
    async for x in itertools.compress([1], [1]):
        assert_type(x, int)


async def test_dropwhile() -> None:
    async for x in itertools.dropwhile(lambda x: True, [1]):
        assert_type(x, int)


async def test_filterfalse() -> None:
    async for x in itertools.filterfalse(lambda x: True, [1]):
        assert_type(x, int)


async def test_starmap() -> None:
    def f(x: str) -> int:
        return int(x)

    async for x in itertools.starmap(f, [("1",)]):
        assert_type(x, int)


async def test_takewhile() -> None:
    async for x in itertools.takewhile(lambda x: True, [1]):
        assert_type(x, int)


async def test_tee() -> None:
    async for x in itertools.tee([1])[0]:
        assert_type(x, int)


async def test_pairwise() -> None:
    async for x in itertools.pairwise([1]):
        assert_type(x, "tuple[int, int]")


async def test_zip_longest() -> None:
    async for x in itertools.zip_longest([1]):
        assert_type(x, "tuple[int]")


async def test_groupby() -> None:
    async for x in itertools.groupby([1]):
        assert_type(x, "tuple[int, AsyncIterator[int]]")
