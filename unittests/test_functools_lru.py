import sys

import pytest

import asyncstdlib as a

from .utility import sync


def method_counter(size):
    class Counter:
        def __init__(self):
            self._count = 0

        @a.lru_cache(maxsize=size)
        async def count(self):
            self._count += 1
            return self._count

    return Counter


def classmethod_counter(size):
    class Counter:
        _count = 0

        def __init__(self):
            type(self)._count = 0

        @classmethod
        @a.lru_cache(maxsize=size)
        async def count(cls):
            cls._count += 1
            return cls._count

    return Counter


def staticmethod_counter(size):
    # I'm sorry for writing this test – please don't do this at home!
    _count = 0

    class Counter:
        def __init__(self):
            nonlocal _count
            _count = 0

        @staticmethod
        @a.lru_cache(maxsize=size)
        async def count():
            nonlocal _count
            _count += 1
            return _count

    return Counter


@pytest.mark.parametrize("size", [0, 3, 10, None])
@pytest.mark.parametrize(
    "counter_factory", [method_counter, classmethod_counter, staticmethod_counter]
)
@sync
async def test_method(size, counter_factory):
    """Test wrapping various method kinds"""

    counter_type = counter_factory(size)
    # caching without resetting
    for _instance in range(4):
        instance = counter_type()
        for reset in range(5):
            for access in range(5):
                misses = 1 if size != 0 else reset * 5 + access + 1
                assert misses == await instance.count()
    counter_type.count.cache_clear()
    # caching with resetting everything
    for _instance in range(4):
        instance = counter_type()
        for reset in range(5):
            for access in range(5):
                misses = reset + 1 if size != 0 else reset * 5 + access + 1
                assert misses == await instance.count()
            instance.count.cache_clear()
    counter_type.count.cache_clear()
    # classmethod does not respect descriptors up to 3.8
    if sys.version_info >= (3, 9) or not isinstance(
        counter_type.__dict__["count"], classmethod
    ):
        # caching with resetting specific item
        for _instance in range(4):
            instance = counter_type()
            for reset in range(5):
                for access in range(5):
                    misses = reset * 5 + access + 1
                    assert misses == await instance.count()
                    instance.count.cache_discard()
    counter_type.count.cache_clear()
