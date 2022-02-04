import pytest

import asyncstdlib as a

from .utility import sync, asyncify


CLOSED = "closed"


@sync
async def test_scoped_iter_iterclose():
    """A `scoped_iter` cannot be closed via its public interface"""
    async_iterable, iterable = asyncify(range(10)), iter(range(10))
    async with a.scoped_iter(async_iterable) as a1:
        assert await a.anext(a1) == next(iterable)
        # closing a scoped iterator is a no-op
        await a1.aclose()
        assert await a.anext(a1) == next(iterable)
        # explicitly test #68
        await a.iter(a1).aclose()
        assert await a.anext(a1) == next(iterable)
        assert await a.list(async_iterable) == list(iterable)
    assert await a.anext(a1, CLOSED) == CLOSED
    assert await a.anext(async_iterable, CLOSED) == CLOSED


@sync
async def test_nested_lifetime():
    async_iterable, iterable = asyncify(range(10)), iter(range(10))
    async with a.scoped_iter(async_iterable) as a1:
        assert await a.anext(a1) == next(iterable)
        async with a.scoped_iter(a1) as a2:
            assert await a.anext(a2) == next(iterable)
            assert await a.anext(a1) == next(iterable)
            # scoped iter can only be closed by scope
            await a2.aclose()
            assert await a.anext(a2) == next(iterable)
        # scoped iterator is closed by its own scope
        assert await a.anext(a2, CLOSED) == CLOSED
        # scoped iterator is not implicitly closed by inner scope
        assert await a.anext(a1) == next(iterable)
        assert await a.anext(async_iterable) == next(iterable)
    assert await a.anext(a2, CLOSED) == CLOSED
    assert await a.anext(a1, CLOSED) == CLOSED
    assert await a.anext(async_iterable, CLOSED) == CLOSED


@sync
async def test_nested_lifetime_closed_outer():
    """outer lifetime restricts inner lifetime"""
    async_iterable, iterable = asyncify(range(10)), iter(range(10))
    async with a.scoped_iter(async_iterable) as a1:
        assert await a.anext(a1) == next(iterable)
        b1 = a.borrow(a1)
        async with a.scoped_iter(b1) as a2:
            assert await a.anext(a2) == next(iterable)
            await b1.aclose()
            # scope iterator is closed alongside parent
            assert await a.anext(a2, CLOSED) == CLOSED
            assert await a.anext(b1, CLOSED) == CLOSED
        assert await a.anext(a2, CLOSED) == CLOSED
        assert await a.anext(b1, CLOSED) == CLOSED
        # scoped iterator is not implicitly closed by inner scope/borrow
        assert await a.anext(a1) == next(iterable)
        assert await a.anext(async_iterable) == next(iterable)
    assert await a.anext(a2, CLOSED) == CLOSED
    assert await a.anext(a1, CLOSED) == CLOSED
    assert await a.anext(async_iterable, CLOSED) == CLOSED


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


@sync
async def test_await_each():
    async def check1() -> bool:
        return True

    async def check2() -> bool:
        return True

    async def check3() -> bool:
        return True

    all_non_negative = await a.all(a.await_each([check1(), check2(), check3()]))

    assert all_non_negative


@sync
async def test_apply_with_no_arguments():
    # This is probably a meaningless use case, but we want to make sure that
    # ``apply`` is still robust.
    result = await a.apply(lambda: 42)

    assert result == 42


@sync
async def test_apply_with_an_argument():
    async def compute_something() -> int:
        return 42

    result = await a.apply(lambda x: 2 * x, compute_something())

    assert result == 84


@sync
async def test_apply_with_keyword_arguments():
    async def compute_something() -> int:
        return 42

    async def compute_something_else() -> int:
        return 1984

    result = await a.apply(
        lambda x, y: x - y, x=compute_something(), y=compute_something_else()
    )

    assert result == 42 - 1984


@sync
async def test_apply_with_an_argument_and_a_keyword_argument():
    async def compute_something() -> int:
        return 42

    async def compute_something_else() -> int:
        return 1984

    result = await a.apply(
        lambda x, y: x - y, compute_something(), y=compute_something_else()
    )

    assert result == 42 - 1984


@sync
async def test_sync():
    def check_3(x: int) -> int:
        return x + 10

    async def check_4(x: int, y: int, z: int) -> int:
        return x + y + z + 100

    t1 = await a.sync(check_3)(x=100)
    t2 = await a.sync(check_4)(x=5, y=5, z=10)
    t3 = await a.sync(lambda x: x**3)(x=5)

    with pytest.raises(TypeError):
        a.sync("string")(10)

    assert t1 == 110
    assert t2 == 120
    assert t3 == 125


@sync
async def test_sync_awaitable():
    """Test any (…) -> await T is recognised"""

    @a.sync
    def nocoro_async(value):
        async def coro():
            return value

        return coro()

    assert await nocoro_async(5) == 5


async def await_iter(n: int):
    return [*range(n)]


async def async_iter(n: int):
    for i in range(n):
        yield i


async def await_value(i):
    return i


async def await_iter_await(n: int):
    return [await_value(i) for i in range(n)]


async def await_async_iter_await(n: int):
    for i in range(n):
        yield await_value(i)


@pytest.mark.parametrize("n", [0, 1, 12])
@pytest.mark.parametrize(
    "any_iterable_t",
    [range, await_iter, async_iter, await_iter_await, await_async_iter_await],
)
@sync
async def test_any_iter(n, any_iterable_t):
    iterable = any_iterable_t(n)
    assert [item async for item in a.any_iter(iterable)] == [*range(n)]
