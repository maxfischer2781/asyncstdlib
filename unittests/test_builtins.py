import pytest

import asyncitertools as a

from .utility import sync, asyncify


@sync
async def test_all():
    assert await a.all(asyncify((True, True, True)))
    assert not await a.all(asyncify((True, False, True)))


@sync
async def test_any():
    assert await a.any(asyncify((False, True, False)))
    assert not await a.any(asyncify((False, False, False)))


@sync
async def test_map_as():
    async def map_op(value):
        return value * 2

    assert [value async for value in a.map(map_op, range(5))] == list(range(0, 10, 2))
    assert [value async for value in a.map(map_op, range(5, 10, 2))] == list(
        range(10, 20, 4)
    )


@sync
async def test_map_sa():
    def map_op(value):
        return value * 2

    assert [value async for value in a.map(map_op, asyncify(range(5)))] == list(
        range(0, 10, 2)
    )
    assert [value async for value in a.map(map_op, asyncify(range(5, 10, 2)))] == list(
        range(10, 20, 4)
    )


@sync
async def test_map_aa():
    async def map_op(value):
        return value * 2

    assert [value async for value in a.map(map_op, asyncify(range(5)))] == list(
        range(0, 10, 2)
    )
    assert [value async for value in a.map(map_op, asyncify(range(5, 10, 2)))] == list(
        range(10, 20, 4)
    )


@sync
async def test_max_default():
    assert await a.max((), default=3) == 3
    assert await a.max((), key=lambda x: x, default=3) == 3
    with pytest.raises(ValueError):
        assert await a.max(()) == 3
    with pytest.raises(ValueError):
        assert await a.max((), key=lambda x: x) == 3


@sync
async def test_max_sa():
    async def minus(x):
        return -x

    assert await a.max(asyncify((1, 2, 3, 4))) == 4
    assert await a.max(asyncify((1, 4, 3, 2))) == 4
    assert await a.max(asyncify((1, 2, 3, 4)), key=lambda x: -x) == 1
    assert await a.max(asyncify((4, 2, 3, 1)), key=lambda x: -x) == 1
    assert await a.max(asyncify((1, 2, 3, 4)), key=minus) == 1
    assert await a.max(asyncify((4, 2, 3, 1)), key=minus) == 1


@sync
async def test_filter_as():
    async def map_op(value):
        return value % 2 == 0

    assert [value async for value in a.filter(map_op, range(5))] == list(range(0, 5, 2))
    assert [value async for value in a.filter(map_op, range(5, 10, 2))] == []
    assert [value async for value in a.filter(map_op, range(4, 10, 2))] == list(
        range(4, 10, 2)
    )


@sync
async def test_filter_sa():
    def map_op(value):
        return value % 2 == 0

    assert [value async for value in a.filter(map_op, asyncify(range(5)))] == list(
        range(0, 5, 2)
    )
    assert [value async for value in a.filter(map_op, asyncify(range(5, 10, 2)))] == []
    assert [
        value async for value in a.filter(map_op, asyncify(range(4, 10, 2)))
    ] == list(range(4, 10, 2))


@sync
async def test_filter_aa():
    async def map_op(value):
        return value % 2 == 0

    assert [value async for value in a.filter(map_op, asyncify(range(5)))] == list(
        range(0, 5, 2)
    )
    assert [value async for value in a.filter(map_op, asyncify(range(5, 10, 2)))] == []
    assert [
        value async for value in a.filter(map_op, asyncify(range(4, 10, 2)))
    ] == list(range(4, 10, 2))


@sync
async def test_filter_na():
    assert [value async for value in a.filter(None, asyncify(range(5)))] == list(
        range(1, 5)
    )
    assert [value async for value in a.filter(None, asyncify(range(5, 10, 2)))] == list(
        range(5, 10, 2)
    )
    assert [value async for value in a.filter(None, asyncify(range(-10, 10)))] == list(
        range(-10, 0)
    ) + list(range(1, 10))


@sync
async def test_enumerate():
    async for count, value in a.enumerate(asyncify(range(5))):
        assert count == value
    async for count, value in a.enumerate(asyncify(range(5, 10)), start=5):
        assert count == value
