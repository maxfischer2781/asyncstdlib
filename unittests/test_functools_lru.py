import pytest

import asyncstdlib as a

from .utility import sync


@pytest.mark.parametrize("size", [0, 3, 10, None])
@sync
async def test_method(size):
    """Test wrapping a method"""

    class Counter:
        def __init__(self):
            self._count = 0

        @a.lru_cache(maxsize=size)
        async def count(self):
            self._count += 1
            return self._count

    for _instance in range(4):
        instance = Counter()
        for reset in range(5):
            for access in range(5):
                misses = reset + 1 if size != 0 else reset * 5 + access + 1
                assert misses == await instance.count()
            instance.count.cache_clear()
