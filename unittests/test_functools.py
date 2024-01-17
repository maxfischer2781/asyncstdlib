import functools

import pytest

import asyncstdlib as a

from .utility import sync, asyncify, multi_sync, Switch, Schedule


@sync
async def test_cached_property():
    class Pair:
        def __init__(self, a, b):
            self.a = a
            self.b = b

        @a.cached_property
        async def total(self):
            return self.a + self.b

    pair = Pair(1, 2)
    assert (await pair.total) == 3
    pair.a = 2
    assert (await pair.total) == 3
    del pair.total
    assert (await pair.total) == 4
    assert type(Pair.total) is a.cached_property


@sync
async def test_cache_property_nodict():
    # note: The exact error is version- and possibly implementation-dependent.
    #       Some Python version wrap all errors from __set_name__.
    with pytest.raises(Exception):  # noqa: B017

        class Pair:
            __slots__ = "a", "b"

            def __init__(self, a, b):
                pass  # pragma: no cover

            @a.cached_property
            async def total(self):
                pass  # pragma: no cover


@multi_sync
async def test_cache_property_order():
    class Value:
        def __init__(self, value):
            self.value = value

        @a.cached_property
        async def cached(self):
            value = self.value
            await Switch()
            return value

    async def check_increment(to):
        val.value = to
        assert (await val.cached) == to

    val = Value(0)
    await Schedule(check_increment(5), check_increment(12), check_increment(1337))
    assert (await val.cached) != 0
    assert (await val.cached) == 1337  # last value fetched


@sync
async def test_reduce():
    async def reduction(x, y):
        return x + y

    for reducer in (reduction, lambda x, y: x + y):
        for itertype in (asyncify, list):
            assert await a.reduce(reducer, itertype([0, 1])) == functools.reduce(
                lambda x, y: x + y, [0, 1]
            )
            assert await a.reduce(
                reducer, itertype([0, 1, 2, 3, 4, 0, -5])
            ) == functools.reduce(lambda x, y: x + y, [0, 1, 2, 3, 4, 0, -5])
            assert await a.reduce(reducer, itertype([1]), 23) == functools.reduce(
                lambda x, y: x + y, [1], 23
            )
            assert await a.reduce(reducer, itertype([12])) == functools.reduce(
                lambda x, y: x + y, [12]
            )
            assert await a.reduce(reducer, itertype([]), 42) == functools.reduce(
                lambda x, y: x + y, [], 42
            )


@sync
async def test_reduce_misuse():
    with pytest.raises(TypeError):
        await a.reduce(lambda x, y: x + y, [])
    with pytest.raises(TypeError):
        await a.reduce(lambda x, y: x + y, asyncify([]))
    # make sure the stdlib behaves the same
    with pytest.raises(TypeError):
        functools.reduce(lambda x, y: x + y, [])


@sync
async def test_lru_cache_bounded():
    calls = []

    @a.lru_cache(maxsize=4)
    async def pingpong(*args, **kwargs):
        calls.append(args[0])
        return args, kwargs

    for kwargs in ({}, {"foo": "bar"}, {"foo": "bar", "baz": 12}):
        for val in range(4):
            assert await pingpong(val, **kwargs) == ((val,), kwargs)
            assert pingpong.cache_info().hits == 0
            assert pingpong.cache_info().misses == val + 1
        assert len(calls) == 4
        for idx in range(5):
            for val in range(4):
                assert await pingpong(val, **kwargs) == ((val,), kwargs)
            assert len(calls) == 4
            assert pingpong.cache_info().hits == (idx + 1) * 4
        for idx in range(5):
            for val in range(4, 9):
                assert await pingpong(val, val, **kwargs) == ((val, val), kwargs)
            assert len(calls) == (idx + 1) * 5 + 4

        calls.clear()
        pingpong.cache_clear()
        assert pingpong.cache_info().hits == 0
        assert pingpong.cache_info().misses == 0


@sync
async def test_lru_cache_unbounded():
    calls = []

    @a.lru_cache(maxsize=None)
    async def pingpong(*args, **kwargs):
        calls.append(args[0])
        return args, kwargs

    for kwargs in ({}, {"foo": "bar"}, {"foo": "bar", "baz": 12}):
        for val in range(4):
            assert await pingpong(val, **kwargs) == ((val,), kwargs)
            assert pingpong.cache_info().hits == 0
            assert pingpong.cache_info().misses == val + 1
        for idx in range(5):
            for val in range(4):
                assert await pingpong(val, **kwargs) == ((val,), kwargs)
            assert len(calls) == 4
            assert pingpong.cache_info().hits == (idx + 1) * 4
        for _ in range(5):
            for val in range(4, 9):
                assert await pingpong(val, val, **kwargs) == ((val, val), kwargs)
            assert len(calls) == 9

        calls.clear()
        pingpong.cache_clear()
        assert pingpong.cache_info().hits == 0
        assert pingpong.cache_info().misses == 0


@sync
async def test_lru_cache_empty():
    calls = []

    @a.lru_cache(maxsize=0)
    async def pingpong(*args, **kwargs):
        calls.append(args[0])
        return args, kwargs

    for val in range(20):
        assert await pingpong(val) == ((val,), {})
        assert pingpong.cache_info().hits == 0
        assert pingpong.cache_info().misses == val + 1
    assert len(calls) == 20 == pingpong.cache_info().misses
    for idx in range(5):
        for val in range(5):
            assert await pingpong(val) == ((val,), {})
            assert len(calls) == 20 + idx * 5 + val + 1
            assert pingpong.cache_info().misses == 20 + idx * 5 + val + 1

    calls.clear()
    pingpong.cache_clear()
    assert pingpong.cache_info().hits == 0
    assert pingpong.cache_info().misses == 0


@sync
async def test_lru_cache_typed():
    @a.lru_cache(maxsize=4, typed=True)
    async def pingpong(arg):
        return arg

    for val in range(20):
        assert await pingpong(val) == val
        assert await pingpong(float(val)) == val
        assert pingpong.cache_info().misses == (val + 1) * 2
        assert pingpong.cache_info().hits == val * 2
        assert await pingpong(val) == val
        assert await pingpong(float(val)) == val
        assert pingpong.cache_info().misses == (val + 1) * 2
        assert pingpong.cache_info().hits == (val + 1) * 2


@sync
async def test_lru_cache_method():
    """
    Test that the lru_cache can be used on methods
    """

    class SelfCached:
        def __init__(self, ident: int):
            self.ident = ident

        @a.lru_cache()
        async def pingpong(self, arg):
            # return identifier of instance to separate cache entries per instance
            return arg, self.ident

    for iteration in range(4):
        instance = SelfCached(iteration)
        for val in range(20):
            # 1 read initializes, 2 reads hit
            assert await instance.pingpong(val) == (val, iteration)
            assert await instance.pingpong(float(val)) == (val, iteration)
            assert await instance.pingpong(val) == (val, iteration)
            assert instance.pingpong.cache_info().misses == val + 1 + 20 * iteration
            assert instance.pingpong.cache_info().hits == (val + 1 + 20 * iteration) * 2


@sync
async def test_lru_cache_bare():
    @a.lru_cache
    async def pingpong(arg):
        return arg

    # check that we are properly wrapped
    assert pingpong.cache_info().hits == 0
    assert pingpong.cache_info().misses == 0


@sync
async def test_lru_cache_misuse():
    with pytest.raises(TypeError):

        @a.lru_cache(maxsize=1.5)
        async def pingpong(arg):
            return arg


@pytest.mark.parametrize("size", [16, None])
@multi_sync
async def test_lru_cache_concurrent(size):
    current = 0

    @a.lru_cache(maxsize=size)
    async def count():
        nonlocal current
        value = current = current + 1
        await Switch()
        return value

    async def verify(expected):
        assert (await count()) == expected

    await Schedule(*(verify(n + 1) for n in range(5)))
    await verify(6)
    await Switch()
    await verify(1)


@sync
async def test_cache():
    calls = []

    @a.cache
    async def pingpong(*args, **kwargs):
        calls.append(args[0])
        return args, kwargs

    for kwargs in ({}, {"one": 1}, {"one": 1, "two": 2}):
        # fill with initial argument patterns
        for val in range(4):
            assert await pingpong(val, **kwargs) == ((val,), kwargs)
            assert len(calls) == val + 1
            assert pingpong.cache_info().hits == 0
            assert pingpong.cache_info().misses == val + 1
        # repeat argument patterns several times
        for idx in range(5):
            for val in range(4):
                assert await pingpong(val, **kwargs) == ((val,), kwargs)
            assert len(calls) == 4
            assert pingpong.cache_info().hits == (idx + 1) * 4
        # fill with new argument patterns
        for _ in range(5):
            for val in range(4, 9):
                assert await pingpong(val, val, **kwargs) == ((val, val), kwargs)
            assert len(calls) == 9

        calls.clear()
        pingpong.cache_clear()
        assert pingpong.cache_info().hits == 0
        assert pingpong.cache_info().misses == 0


metadata_cases = [
    (a.cache, None),
    (lambda func: a.lru_cache(None)(func), None),
    (lambda func: a.lru_cache(0)(func), 0),
    (lambda func: a.lru_cache(1)(func), 1),
    (lambda func: a.lru_cache(256)(func), 256),
]


@pytest.mark.parametrize("cache, maxsize", metadata_cases)
def test_caches_metadata(cache, maxsize):
    @cache
    async def pingpong(*args, **kwargs):
        return args, kwargs

    assert pingpong.cache_info().maxsize == pingpong.cache_parameters()["maxsize"]
    assert not pingpong.cache_parameters()["typed"]
    # state for unfilled cache should always be the same
    assert pingpong.cache_info().hits == 0
    assert pingpong.cache_info().misses == 0
    assert pingpong.cache_info().currsize == 0
