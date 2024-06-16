from typing import Callable, Any
import sys

import pytest

import asyncstdlib as a

from .utility import sync


class Counter:
    kind: object
    count: Any


def method_counter(size: "int | None") -> "type[Counter]":
    class Counter:
        kind = None

        def __init__(self):
            self._count = 0

        @a.lru_cache(maxsize=size)
        async def count(self):
            self._count += 1
            return self._count

    return Counter


def classmethod_counter(size: "int | None") -> "type[Counter]":
    class Counter:
        _count = 0
        kind = classmethod

        def __init__(self):
            type(self)._count = 0

        @classmethod
        @a.lru_cache(maxsize=size)
        async def count(cls):
            cls._count += 1
            return cls._count

    return Counter


def staticmethod_counter(size: "int | None") -> "type[Counter]":
    # I'm sorry for writing this test – please don't do this at home!
    count: int = 0

    class Counter:
        kind = staticmethod

        def __init__(self):
            nonlocal count
            count = 0

        @staticmethod
        @a.lru_cache(maxsize=size)
        async def count():
            nonlocal count
            count += 1
            return count

    return Counter


counter_factories: "list[Callable[[int | None], type[Counter]]]" = [
    method_counter,
    classmethod_counter,
    staticmethod_counter,
]


@pytest.mark.parametrize("size", [0, 3, 10, None])
@pytest.mark.parametrize("counter_factory", counter_factories)
@sync
async def test_method_plain(
    size: "int | None", counter_factory: "Callable[[int | None], type[Counter]]"
):
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
async def test_method_clear(
    size: "int | None", counter_factory: "Callable[[int | None], type[Counter]]"
):
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
async def test_method_discard(
    size: "int | None", counter_factory: "Callable[[int | None], type[Counter]]"
):
    """Test caching with resetting specific item"""
    counter_type = counter_factory(size)
    if not (
        (3, 9) <= sys.version_info[:2] <= (3, 12)
        or counter_type.kind is not classmethod
    ):
        pytest.skip("classmethod only respects descriptors between 3.9 and 3.12")
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
async def test_method_metadata(
    size: "int | None", counter_factory: "Callable[[int | None], type[Counter]]"
):
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
def test_wrapper_attributes(size: "int | None"):
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
