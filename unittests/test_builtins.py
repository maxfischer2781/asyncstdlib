import random

import pytest

import asyncstdlib as a

from .utility import sync, asyncify, awaitify, inside_loop


def hide_coroutine(corofunc):
    def wrapper(*args, **kwargs):
        return corofunc(*args, **kwargs)

    return wrapper


@sync
async def test_iter1():
    for iterable in ([], [1, 2, 5, 20], range(20)):
        assert await a.list(a.iter(iterable)) == list(iterable)
        assert await a.list(a.iter(asyncify(iterable))) == list(iterable)


@sync
async def test_iter2():
    for call, sentinel in (
        (lambda: lambda: 1, 1),
        (lambda: lambda x=[]: x.append(1) or len(x), 5),
    ):
        assert await a.list(a.iter(call(), sentinel)) == list(iter(call(), sentinel))
        assert await a.list(a.iter(awaitify(call()), sentinel)) == list(
            iter(call(), sentinel)
        )
    with pytest.raises(TypeError):
        a.iter(1, 1)


@sync
async def test_all():
    assert await a.all(asyncify((True, True, True)))
    assert not await a.all(asyncify((True, False, True)))


@sync
async def test_any():
    assert await a.any(asyncify((False, True, False)))
    assert not await a.any(asyncify((False, False, False)))


@sync
async def test_zip():
    async for va, vb in a.zip(asyncify(range(5)), range(5)):
        assert va == vb
    async for idx, vs in a.enumerate(a.zip(asyncify(range(5)), range(5))):
        assert vs[0] == vs[1] == idx
    async for _ in a.zip():
        assert False


@sync
async def test_zip_strict():
    async for va, vb in a.zip(asyncify(range(5)), range(5), strict=True):
        assert va == vb
    with pytest.raises(ValueError):
        async for _ in a.zip(asyncify(range(5)), range(6), strict=True):
            pass
    with pytest.raises(ValueError):
        async for _ in a.zip(asyncify(range(6)), range(5), strict=True):
            pass
    with pytest.raises(ValueError):
        async for _ in a.zip(*[range(5)] * 6, range(6), strict=True):
            pass


@sync
async def test_zip_close_immediately():
    closed = False

    class SomeIterable:
        async def __aiter__(self):
            try:
                while True:
                    yield 1
            finally:
                nonlocal closed
                if await inside_loop():
                    closed = True

    zip_iter = a.zip(asyncify(range(-5, 0)), SomeIterable())
    async for va, vb in zip_iter:
        assert va < 0
        assert vb == 1
    assert closed is True


@sync
async def test_map_as():
    async def map_op(value):
        return value * 2

    assert [value async for value in a.map(map_op, range(5))] == list(range(0, 10, 2))
    assert [
        value async for value in a.map(hide_coroutine(map_op), range(5, 10, 2))
    ] == list(range(10, 20, 4))


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
    assert [
        value
        async for value in a.map(hide_coroutine(map_op), asyncify(range(5, 10, 2)))
    ] == list(range(10, 20, 4))


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
async def test_min_default():
    assert await a.min((), default=3) == 3
    assert await a.min((), key=lambda x: x, default=3) == 3
    # default does not override items
    assert await a.min((3, 2, 1), default=3) == 1
    with pytest.raises(ValueError):
        assert await a.min(()) == 3
    with pytest.raises(ValueError):
        assert await a.min((), key=lambda x: x) == 3


@sync
async def test_min_sa():
    async def minus(x):
        return -x

    assert await a.min(asyncify((1, 2, 3, 4))) == 1
    assert await a.min(asyncify((4, 1, 3, 2))) == 1
    assert await a.min(asyncify((1, 2, 3, 4)), key=lambda x: -x) == 4
    assert await a.min(asyncify((4, 2, 3, 1)), key=lambda x: -x) == 4
    assert await a.min(asyncify((1, 2, 3, 4)), key=minus) == 4
    assert await a.min(asyncify((4, 2, 3, 1)), key=minus) == 4


@sync
async def test_filter_as():
    async def map_op(value):
        return value % 2 == 0

    assert [value async for value in a.filter(map_op, range(5))] == list(range(0, 5, 2))
    assert [
        value async for value in a.filter(hide_coroutine(map_op), range(5, 10, 2))
    ] == []
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
        value
        async for value in a.filter(hide_coroutine(map_op), asyncify(range(4, 10, 2)))
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


@sync
async def test_sum():
    assert await a.sum(asyncify((1, 2, 3, 4))) == 10
    assert await a.sum(asyncify((4, 3, 2, 1)), start=5) == 15
    assert await a.sum((), start=5) == 5


@sync
async def test_types():
    assert await a.list(asyncify(range(5))) == list(range(5))
    assert await a.list(asyncify(range(0))) == list(range(0))
    assert await a.list() == list()
    assert await a.tuple(asyncify(range(5))) == tuple(range(5))
    assert await a.tuple(asyncify(range(0))) == tuple(range(0))
    assert await a.tuple() == tuple()
    assert await a.set(asyncify(range(5))) == set(range(5))
    assert await a.set(asyncify(range(0))) == set(range(0))
    assert await a.set() == set()
    assert await a.dict(a.zip((str(i) for i in range(5)), range(5))) == dict(
        zip((str(i) for i in range(5)), range(5))
    )
    assert await a.dict(a.zip((str(i) for i in range(0)), range(0))) == dict(
        zip((str(i) for i in range(0)), range(0))
    )
    assert await a.dict(b=3) == dict(b=3)
    assert await a.dict(a.zip((str(i) for i in range(5)), range(5)), b=3) == dict(
        zip((str(i) for i in range(5)), range(5)), b=3
    )
    assert await a.dict() == dict()


sortables = [
    [],
    [0],
    [1, 4, 17, -12, 3, 47, -98, 72, -1138],
    list(range(20)),
    list(range(2000)),
    [random.random() for _ in range(2000)],
]


@pytest.mark.parametrize("sortable", sortables)
@pytest.mark.parametrize("reverse", [True, False])
@sync
async def test_sorted_direct(sortable, reverse):
    assert await a.sorted(sortable, reverse=reverse) == sorted(
        sortable, reverse=reverse
    )
    assert await a.sorted(asyncify(sortable), reverse=reverse) == sorted(
        sortable, reverse=reverse
    )
    assert await a.sorted(sortable, key=lambda x: x, reverse=reverse) == sorted(
        sortable, key=lambda x: x, reverse=reverse
    )
    assert await a.sorted(
        sortable, key=awaitify(lambda x: x), reverse=reverse
    ) == sorted(sortable, key=lambda x: x, reverse=reverse)


@sync
async def test_sorted_stable():
    values = [-i for i in range(20)]

    def collision_key(x):
        return x // 2

    # test the test...
    assert sorted(values, key=collision_key) != [
        item for key, item in sorted([(collision_key(i), i) for i in values])
    ]
    # test the implementation
    assert await a.sorted(values, key=awaitify(collision_key)) == sorted(
        values, key=collision_key
    )
