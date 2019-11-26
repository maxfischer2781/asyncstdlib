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
