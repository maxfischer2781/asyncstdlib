from asyncio import iscoroutinefunction
from functools import wraps
from typing import (
    Union,
    AsyncIterator,
    TypeVar,
    AsyncGenerator,
    Iterable,
    Awaitable,
    AsyncIterable,
    Callable,
    Any,
    overload,
    Optional,
)

from ._typing import AsyncContextManager, T, T1, T2, T3, T4, T5, AnyIterable
from ._core import aiter
from .contextlib import nullcontext


S = TypeVar("S")


class _BorrowedAsyncIterator(AsyncGenerator[T, S]):
    """
    Borrowed async iterator/generator, preventing to ``aclose`` the ``iterable``
    """

    # adding special methods such as `__anext__` as `__slots__` allows to set them
    # on the instance: the interpreter expects *descriptors* not methods, and
    # `__slots__` are descriptors just like methods.
    __slots__ = "__wrapped__", "__anext__", "asend", "athrow", "_wrapper"

    # Type checker does not understand `__slot__` definitions
    __anext__: Callable[[Any], Awaitable[T]]
    asend: Any
    athrow: Any

    def __init__(self, iterator: Union[AsyncIterator[T], AsyncGenerator[T, S]]):
        self.__wrapped__ = iterator
        # Create an actual async generator wrapper that we can close. Otherwise,
        # if we pass on the original iterator methods we cannot disable them if
        # anyone has a reference to them.
        self._wrapper: AsyncGenerator[T, S] = self._wrapped_iterator(iterator)
        # Forward all async iterator/generator methods but __aiter__ and aclose:
        # An async *iterator* (e.g. `async def: yield`) must return
        # itself from __aiter__. If we do not shadow this then
        # running aiter(self).aclose closes the underlying iterator.
        self.__anext__ = self._wrapper.__anext__  # type: ignore
        if hasattr(iterator, "asend"):
            self.asend = iterator.asend
        if hasattr(iterator, "athrow"):
            self.athrow = iterator.athrow

    # Py3.6 compatibility
    # Use ``(item async for item in iterator)`` inside
    # ``__init__`` when no longer needed.
    @staticmethod
    async def _wrapped_iterator(
        iterator: Union[AsyncIterator[T], AsyncGenerator[T, S]]
    ) -> AsyncGenerator[T, S]:
        async for item in iterator:
            yield item

    def __aiter__(self) -> AsyncGenerator[T, S]:
        return self

    def __repr__(self) -> str:
        return f"<asyncstdlib.borrow of {self.__wrapped__!r} at 0x{(id(self)):x}>"

    async def _aclose_wrapper(self) -> None:
        wrapper_iterator = self._wrapper
        # allow closing the intermediate wrapper
        # this prevents a resource warning if the wrapper is GC'd
        # the underlying iterator is NOT affected by this
        await wrapper_iterator.aclose()
        # disable direct asend/athrow to the underlying iterator
        if hasattr(self, "asend"):
            self.asend = wrapper_iterator.asend
        if hasattr(self, "athrow"):
            self.athrow = wrapper_iterator.athrow

    def aclose(self) -> Awaitable[None]:
        return self._aclose_wrapper()


class _ScopedAsyncIterator(_BorrowedAsyncIterator[T, S]):
    __slots__ = ()

    def __repr__(self) -> str:
        return f"<asyncstdlib.scoped_iter of {self.__wrapped__!r} at 0x{(id(self)):x}>"

    async def aclose(self) -> None:
        pass


class _ScopedAsyncIteratorContext(AsyncContextManager[AsyncIterator[T]]):
    """
    Context restricting the lifetime of ``iterator`` to the context scope

    This is an internal helper that relies on ``iterator`` belonging to the scope
    and having an ``aclose`` method.
    """

    __slots__ = "_borrowed_iter", "_iterator"

    def __init__(self, iterator: AsyncIterator[T]):
        self._iterator: AsyncIterator[T] = iterator
        self._borrowed_iter: Optional[_ScopedAsyncIterator[T, Any]] = None

    async def __aenter__(self) -> AsyncIterator[T]:
        if self._borrowed_iter is not None:
            raise RuntimeError("scoped_iter is not re-entrant")
        borrowed_iter = self._borrowed_iter = _ScopedAsyncIterator(self._iterator)
        return borrowed_iter

    async def __aexit__(self, *args: Any) -> bool:
        await self._borrowed_iter._aclose_wrapper()  # type: ignore
        await self._iterator.aclose()  # type: ignore
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} of {self._iterator!r} at 0x{(id(self)):x}>"


def borrow(iterator: AsyncIterator[T]) -> AsyncIterator[T]:
    """
    Borrow an async iterator, preventing to ``aclose`` it

    When :term:`borrowing` an async iterator, the original owner assures
    to close the iterator as needed. In turn, the borrowed iterator does
    not allow closing the underlying iterator.

    The borrowed iterator supports :py:meth:`~agen.asend` and
    :py:meth:`~agen.athrow` if the underlying iterator supports them as well;
    this allows borrowing either an :py:class:`~collections.abc.AsyncIterator`
    or :py:class:`~collections.abc.AsyncGenerator`. Regardless of iterator type,
    :py:meth:`~agen.aclose` is always provided; it closes only the borrowed
    iterator, not the underlying iterator.

    .. seealso:: Use :py:func:`~.scoped_iter` to ensure an (async) iterable
                 is eventually closed and only :term:`borrowed <borrowing>` until then.
    """
    if not hasattr(iterator, "__anext__") or not hasattr(iterator, "__aiter__"):
        raise TypeError(
            "borrowing requires an async iterator "
            + f"with __aiter__ and __anext__ method, got {type(iterator).__name__}"
        )
    return _BorrowedAsyncIterator(iterator)


def scoped_iter(iterable: AnyIterable[T]) -> AsyncContextManager[AsyncIterator[T]]:
    """
    Context manager that provides an async iterator for an (async) ``iterable``

    Roughly equivalent to combining :py:func:`~asyncstdlib.builtins.iter` with
    :py:class:`~asyncstdlib.contextlib.closing`. The resulting
    :term:`asynchronous iterator` is automatically :term:`borrowed <borrowing>`
    to prevent premature closing when passing the iterator around.

    .. code-block:: python3

        from collections import deque
        import asyncstdlib as a

        async def head_tail(iterable, leading=5, trailing=5):
            '''Provide the first ``leading`` and last ``trailing`` items'''
            # create async iterator valid for the entire block
            async with a.scoped_iter(iterable) as async_iter:
                # ... safely pass it on without it being closed ...
                async for item in a.islice(async_iter, leading):
                    yield item
                tail = deque(maxlen=trailing)
                # ... and use it again in the block
                async for item in async_iter:
                    tail.append(item)
            for item in tail:
                yield item

    Nested scoping of the same iterator is safe: inner scopes automatically forfeit
    closing the underlying iterator in favour of the outermost scope. This allows
    passing the scoped iterator to other functions that use :py:func:`scoped_iter`.
    """
    # The iterable has already been borrowed.
    # Do not unwrap it to preserve method forwarding.
    if isinstance(iterable, (_BorrowedAsyncIterator, _ScopedAsyncIterator)):
        return _ScopedAsyncIteratorContext(iterable)
    iterator = aiter(iterable)
    # The iterable cannot be closed.
    # We do not need to take care of it.
    if not hasattr(iterator, "aclose"):
        return nullcontext(iterator)
    return _ScopedAsyncIteratorContext(iterator)


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


def sync(function: Callable[..., T]) -> Callable[..., Any]:
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
    async def async_wrapped(*args: Any, **kwargs: Any) -> T:
        result = function(*args, **kwargs)
        if isinstance(result, Awaitable):
            return await result  # type: ignore
        return result

    return async_wrapped


async def any_iter(
    __iter: Union[
        Awaitable[AnyIterable[Awaitable[T]]],
        Awaitable[AnyIterable[T]],
        AnyIterable[Awaitable[T]],
        AnyIterable[T],
    ]
) -> AsyncIterator[T]:
    """
    Provide an async iterator for various forms of "asynchronous iterable"

    Useful to uniformly handle async iterables, awaitable iterables, iterables of
    awaitables, and similar in an ``async for`` loop. Among other things, this
    matches all forms of ``async def`` functions providing iterables.

    .. code-block:: python3

        import random
        import asyncstdlib as a

        # AsyncIterator[T]
        async def async_iter(n):
            for i in range(n):
                yield i

        # Awaitable[Iterator[T]]
        async def await_iter(n):
            return [*range(n)]

        some_iter = random.choice([async_iter, await_iter, range])
        async for item in a.any_iter(some_iter(4)):
            print(item)

    This function must eagerly resolve each "async layer" before checking if
    the next layer is as expected. This incurs a performance penalty and
    non-iterables may be left unusable by this.
    Prefer :py:func:`~.builtins.iter` to test for iterables with :term:`EAFP`
    and for performance when only simple iterables need handling.
    """
    iterable = __iter if not isinstance(__iter, Awaitable) else await __iter
    if isinstance(iterable, AsyncIterable):
        async for item in iterable:
            yield item if not isinstance(item, Awaitable) else await item
    else:
        for item in iterable:
            yield item if not isinstance(item, Awaitable) else await item
