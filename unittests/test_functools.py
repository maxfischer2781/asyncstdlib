import functools

import pytest

import asyncstdlib as a

from .utility import sync, asyncify


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
            assert await a.reduce(reducer, itertype([1]), 23,) == functools.reduce(
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
