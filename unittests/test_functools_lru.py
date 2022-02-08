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

    await _test_counting(size, Counter)


@pytest.mark.parametrize("size", [0, 3, 10, None])
@sync
async def test_classmethod(size):
    """Test wrapping a method"""

    class Counter:
        _count = 0

        def __init__(self):
            type(self)._count = 0

        @classmethod
        @a.lru_cache(maxsize=size)
        async def count(cls):
            cls._count += 1
            return cls._count

    await _test_counting(size, Counter)


async def _test_counting(size, counter_type):
    for _instance in range(4):
        instance = counter_type()
        for reset in range(5):
            for access in range(5):
                misses = reset + 1 if size != 0 else reset * 5 + access + 1
                assert misses == await instance.count()
            instance.count.cache_clear()
