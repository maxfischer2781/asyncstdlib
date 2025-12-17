from asyncstdlib import functools


@functools.lru_cache()
async def lru_function(a: int) -> int:
    return a


async def test_cache_parameters() -> None:
    await lru_function(12)
    await lru_function("wrong parameter type")  # type: ignore[arg-type]


class TestLRUMethod:
    """
    Test that `lru_cache` works on methods
    """

    @functools.lru_cache()
    async def cached(self, a: int = 0) -> int:
        return a

    async def test_implicit_self(self) -> int:
        return await self.cached()

    async def test_method_parameters(self) -> int:
        await self.cached("wrong parameter type")  # type: ignore[arg-type]
        return await self.cached(12)


async def aadd(a: int, b: int) -> int:
    return a + b


async def test_reduce() -> None:
    await functools.reduce(aadd, [1, 2, 3, 4])
    await functools.reduce(aadd, [1, 2, 3, 4], initial=1)
