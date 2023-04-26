from asyncstdlib import lru_cache


@lru_cache()
async def lru_function(a: int) -> int:
    return a


async def test_cache_parameters() -> None:
    await lru_function(12)
    await lru_function("wrong parameter type")  # type: ignore[arg-type]


class TestLRUMethod:
    """
    Test that `lru_cache` works on methods
    """
    @lru_cache()
    async def cached(self) -> int:
        return 1

    async def test_implicit_self(self) -> int:
        return await self.cached()
