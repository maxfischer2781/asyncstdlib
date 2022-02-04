import asyncstdlib as a

from .utility import sync


@sync
async def test_method():
    """Test wrapping a method"""

    class Counter:
        def __init__(self):
            self._count = 0

        @a.lru_cache
        async def count(self):
            self._count += 1
            return self._count

    for _instance in range(4):
        instance = Counter()
        for _reset in range(5):
            for _access in range(5):
                assert _reset + 1 == await instance.count()
            instance.count.cache_clear()
