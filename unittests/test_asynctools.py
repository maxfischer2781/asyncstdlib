import pytest

import asyncstdlib as a

from .utility import sync, asyncify


@sync
async def test_nested_lifetime():
    async_iterable = asyncify(range(10))
    values = []
    async with a.scoped_iter(async_iterable) as a1:
        values.append(await a.anext(a1))
        async with a.scoped_iter(a1) as a2:
            values.append(await a.anext(a2))
        # original iterator is not closed by inner scope
        async for value in a1:
            values.append(value)
    assert values == list(range(10))


@sync
async def test_borrow_explicitly():
    async_iterable = asyncify(range(10))
    values = []
    borrowed_aiterable = a.borrow(async_iterable)
    values.append(await a.anext(async_iterable))
    values.append(await a.anext(borrowed_aiterable))
    await a.borrow(borrowed_aiterable).aclose()
    values.append(await a.anext(borrowed_aiterable))
    await borrowed_aiterable.aclose()
    values.append(await a.anext(async_iterable))
    assert values == list(range(4))
    async for value in async_iterable:
        values.append(value)
    assert values == list(range(10))


class Uncloseable:
    def __init__(self, iterator):
        self.iterator = iterator

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await a.anext(self.iterator)


@sync
async def test_borrow_iterable():
    async_iterable = Uncloseable(asyncify(range(10)))
    values = []
    async with a.scoped_iter(async_iterable) as a1:
        values.append(await a.anext(a1))
    values.append(await a.anext(a.borrow(async_iterable)))
    assert values == [0, 1]


class Closeable:
    def __init__(self, iterator):
        self.iterator = iterator

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await a.anext(self.iterator)

    async def aclose(self):
        await self.iterator.aclose()


@pytest.mark.parametrize(
    "async_iterable_t",
    [
        lambda: asyncify(range(10)),
        lambda: Closeable(asyncify(range(10))),
        lambda: Uncloseable(asyncify(range(10))),
    ],
)
@sync
async def test_borrow_methods(async_iterable_t):
    async_iterable = async_iterable_t()
    values = []
    async with a.scoped_iter(async_iterable) as a1:
        values.append(await a.anext(a1))
        assert hasattr(a1, "athrow") == hasattr(async_iterable, "athrow")
        assert hasattr(a1, "asend") == hasattr(async_iterable, "asend")
    assert values == [0]


@sync
async def test_scoped_iter_misuse():
    scoped_iter = a.scoped_iter(asyncify(range(5)))
    async with scoped_iter:
        with pytest.raises(RuntimeError):
            async with scoped_iter:
                pytest.fail("may not enter scoped_iter twice")


@sync
async def test_borrow_misuse():
    with pytest.raises(TypeError):
        a.borrow([1, 2, 3])
