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


counter_factories = [method_counter, classmethod_counter, staticmethod_counter]


@pytest.mark.parametrize("size", [0, 3, 10, None])
@pytest.mark.parametrize("counter_factory", counter_factories)
@sync
async def test_method_plain(size, counter_factory):
    """Test caching without resetting"""

    counter_type = counter_factory(size)
    for _instance in range(4):
        instance = counter_type()
        for reset in range(5):
            for access in range(5):
                misses = 1 if size != 0 else reset * 5 + access + 1
                assert misses == await instance.count()


@pytest.mark.parametrize("size", [0, 3, 10, None])
@pytest.mark.parametrize("counter_factory", counter_factories)
@sync
async def test_method_clear(size, counter_factory):
    """Test caching with resetting everything"""
    counter_type = counter_factory(size)
    for _instance in range(4):
        instance = counter_type()
        for reset in range(5):
            for access in range(5):
                misses = reset + 1 if size != 0 else reset * 5 + access + 1
                assert misses == await instance.count()
            instance.count.cache_clear()


@pytest.mark.parametrize("size", [0, 3, 10, None])
@pytest.mark.parametrize("counter_factory", counter_factories)
@sync
async def test_method_discard(size, counter_factory):
    """Test caching with resetting specific item"""
    counter_type = counter_factory(size)
    if (
        sys.version_info < (3, 9)
        and type(counter_type.__dict__["count"]) is classmethod
    ):
        pytest.skip("classmethod does not respect descriptors up to 3.8")
    for _instance in range(4):
        instance = counter_type()
        for reset in range(5):
            for access in range(5):
                misses = reset * 5 + access + 1
                assert misses == await instance.count()
                instance.count.cache_discard()


@pytest.mark.parametrize("size", [0, 3, 10, None])
@pytest.mark.parametrize("counter_factory", counter_factories)
@sync
async def test_method_metadata(size, counter_factory):
    """Test cache metadata on methods"""
    tp = counter_factory(size)
    for instance in range(4):
        ct = tp()
        for reset in range(5):
            for access in range(5):
                await ct.count()
                assert tp.count.__wrapped__ == ct.count.__wrapped__
                assert tp.count.cache_parameters() == ct.count.cache_parameters()
                assert tp.count.cache_info() == ct.count.cache_info()
                assert (
                    ct.count.cache_info().maxsize
                    == ct.count.cache_parameters()["maxsize"]
                    == size
                )
                totals = instance * 25 + reset * 5 + (access + 1)
                hits, misses, *_ = ct.count.cache_info()
                assert totals == hits + misses


@pytest.mark.parametrize("size", [None, 0, 10, 128])
def test_wrapper_attributes(size):
    class Bar:
        @a.lru_cache
        async def method(self, int_arg: int):
            """Method docstring"""

        @a.lru_cache
        async def other_method(self):
            """Method docstring"""

    assert Bar.method.__doc__ == """Method docstring"""
    for name in ("method", "other_method"):
        for cache in (getattr(Bar, name), getattr(Bar(), name)):
            assert cache.__doc__ == """Method docstring"""
            assert cache.__name__ == name
            assert cache.__qualname__.endswith(f"Bar.{name}")
            if name != "method":
                continue
            # test direct and literal annotation styles
            assert Bar.method.__annotations__["int_arg"] in {int, "int"}
            assert Bar().method.__annotations__["int_arg"] in {int, "int"}
