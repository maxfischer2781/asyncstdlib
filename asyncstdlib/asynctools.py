from asyncio import iscoroutinefunction
from functools import wraps
from typing import (
    Iterable,
    Awaitable,
    AsyncIterable,
    Callable,
    Any,
    overload,
)

from ._typing import T, T1, T2, T3, T4, T5
from ._core import borrow, scoped_iter


async def await_each(awaitables: Iterable[Awaitable[T]]) -> AsyncIterable[T]:
    """
    Iterate through ``awaitables`` and await each item

    This converts an *iterable of async* into an *async iterator* of awaited values.
    Consequently, we can apply various functions made for ``AsyncIterable[T]`` to
    ``Iterable[Awaitable[T]]`` as well.

    Example:

    .. code-block:: python3

        import asyncstdlib as a

        async def check1() -> bool:
            ...

        async def check2() -> bool:
            ...

        async def check3() -> bool:
            ...

        okay = await a.all(
            a.await_each([check1(), check2(), check3()])
        )
    """
    for awaitable in awaitables:
        yield await awaitable


@overload
async def apply(
    __func: Callable[[T1], T],
    __arg1: Awaitable[T1],
) -> T:
    ...


@overload
async def apply(
    __func: Callable[[T1, T2], T],
    __arg1: Awaitable[T1],
    __arg2: Awaitable[T2],
) -> T:
    ...


@overload
async def apply(
    __func: Callable[[T1, T2, T3], T],
    __arg1: Awaitable[T1],
    __arg2: Awaitable[T2],
    __arg3: Awaitable[T3],
) -> T:
    ...


@overload
async def apply(
    __func: Callable[[T1, T2, T3, T4], T],
    __arg1: Awaitable[T1],
    __arg2: Awaitable[T2],
    __arg3: Awaitable[T3],
    __arg4: Awaitable[T4],
) -> T:
    ...


@overload
async def apply(
    __func: Callable[[T1, T2, T3, T4, T5], T],
    __arg1: Awaitable[T1],
    __arg2: Awaitable[T2],
    __arg3: Awaitable[T3],
    __arg4: Awaitable[T4],
    __arg5: Awaitable[T5],
) -> T:
    ...


@overload
async def apply(
    __func: Callable[..., T],
    __arg1: Awaitable[Any],
    __arg2: Awaitable[Any],
    __arg3: Awaitable[Any],
    __arg4: Awaitable[Any],
    __arg5: Awaitable[Any],
    *args: Awaitable[Any],
    **kwargs: Awaitable[Any],
) -> T:
    ...


@overload
async def apply(
    __func: Callable[..., T],
    **kwargs: Awaitable[Any],
) -> T:
    ...


async def apply(
    __func: Callable[..., T], *args: Awaitable[Any], **kwargs: Awaitable[Any]
) -> T:
    """
    Await the arguments and keyword arguments and then apply ``func`` on them

    Example:

    .. code-block:: python3

        async def compute_something() -> float:
            ...

        async def compute_something_else() -> float:
            ...

        result = await apply(
            lambda x, y: x ** y,
            compute_something(),
            compute_something_else())

    The function ``apply`` serves, for example, a practical use case when you want to
    chain operations on awaitables and need to pass around the final awaitable
    for further operations.
    """
    return __func(
        *[await arg for arg in args], **{k: await arg for k, arg in kwargs.items()}
    )


@overload
def sync(function: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    ...


@overload
def sync(function: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    ...


def sync(function: Callable) -> Callable[..., Awaitable[T]]:
    r"""
    Wraps a callable to ensure its result can be ``await``\ ed

    Useful to write :term:`async neutral` functions by wrapping callable arguments,
    or to use synchronous functions where asynchronous ones are expected.
    Wrapping a regular function defined using ``def`` or ``lambda`` makes it
    behave roughly as if it were defined using ``async def`` instead.

    Example:

    .. code-block:: python3

        import asyncstdlib as a

        def test1_sync(x, y):
            ...

        async def test1_async(x):
            ...

        async def main():
            await a.sync(test1_sync)(x=1, y=2)
            await a.sync(test1_async)(x=8)
            await a.sync(lambda x: x ** 3)(x=5)

        if __name__ == "__main__":
            asyncio.run(main())
    """
    if not callable(function):
        raise TypeError("function argument should be Callable")

    if iscoroutinefunction(function):
        return function

    @wraps(function)
    async def async_wrapped(*args, **kwargs):
        result = function(*args, **kwargs)
        if isinstance(result, Awaitable):
            return await result
        return result

    return async_wrapped
