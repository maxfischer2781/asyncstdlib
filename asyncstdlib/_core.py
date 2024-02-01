"""
Internal helpers to safely build async abstractions

While some of these helpers have public siblings
(e.g. :py:class:`~.ScopedIter` and :py:func:`~.asynctools.scoped_iter`)
they are purposely kept separate.
Any helpers in this module are *not* bound to maintaining a public interface,
and offer less convenience to save on overhead.
"""

from inspect import iscoroutinefunction
from typing import (
    Any,
    AsyncIterator,
    AsyncGenerator,
    Iterable,
    AsyncIterable,
    Union,
    Generic,
    Optional,
    Awaitable,
    Callable,
    Type,
)
from types import TracebackType

from ._typing import T, AnyIterable


class Sentinel:
    """Placeholder with configurable ``repr``"""

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return self.name


def aiter(subject: AnyIterable[T]) -> AsyncIterator[T]:
    """
    An async iterator object yielding elements from ``subject``

    :raises TypeError: if ``subject`` does not support any iteration protocol

    The ``subject`` must support
    the async iteration protocol (the :py:meth:`object.__aiter__` method),
    the regular iteration protocol (the :py:meth:`object.__iter__` method),
    or it must support the sequence protocol (the :py:meth:`object.__getitem__`
    method with integer arguments starting at 0).
    In either case, an async iterator is returned.
    """
    if isinstance(subject, AsyncIterable):
        return subject.__aiter__()
    else:
        return _aiter_sync(subject).__aiter__()


async def _aiter_sync(iterable: Iterable[T]) -> AsyncIterator[T]:
    """Helper to provide an async iterator for a regular iterable"""
    for item in iterable:
        yield item


class ScopedIter(Generic[T]):
    """
    Context manager that provides and cleans up an iterator for an iterable

    Note that unlike :py:func:`~.asynctools.scoped_iter`, this helper does
    *not* borrow the iterator automatically. Use :py:func:`~.borrow` if needed.
    """

    __slots__ = ("_iterator",)

    def __init__(self, iterable: AnyIterable[T]):
        self._iterator: AsyncIterator[T] = aiter(iterable)

    async def __aenter__(self) -> AsyncIterator[T]:
        return self._iterator

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        try:
            aclose = self._iterator.aclose()  # type: ignore
        except AttributeError:
            pass
        else:
            await aclose


def borrow(iterator: AsyncIterator[T]) -> AsyncGenerator[T, None]:
    """Borrow an async iterator for iteration, preventing it from being closed"""
    return (item async for item in iterator)


def awaitify(
    function: Union[Callable[..., T], Callable[..., Awaitable[T]]]
) -> Callable[..., Awaitable[T]]:
    """Ensure that ``function`` can be used in ``await`` expressions"""
    if iscoroutinefunction(function):
        return function
    else:
        return Awaitify(function)


class Awaitify(Generic[T]):
    """Helper to peek at the return value of ``function`` and make it ``async``"""

    __slots__ = "__wrapped__", "_async_call"

    def __init__(self, function: Union[Callable[..., T], Callable[..., Awaitable[T]]]):
        self.__wrapped__ = function
        self._async_call: Optional[Callable[..., Awaitable[T]]] = None

    def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[T]:
        if (async_call := self._async_call) is None:
            value = self.__wrapped__(*args, **kwargs)
            if isinstance(value, Awaitable):
                self._async_call = self.__wrapped__  # type: ignore
                return value
            else:
                self._async_call = force_async(self.__wrapped__)  # type: ignore
                return await_value(value)
        else:
            return async_call(*args, **kwargs)


async def await_value(value: T) -> T:
    return value


def force_async(call: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    async def async_wrapped(*args: Any, **kwargs: Any) -> T:
        return call(*args, **kwargs)

    return async_wrapped
