from asyncstdlib import lru_cache


class LRUMethod:
    """
    Test that `lru_cache` works on methods
    """
    @lru_cache()
    async def cached(self) -> int:
        return 1

    async def test_implicit_self(self) -> int:
        return await self.cached()
