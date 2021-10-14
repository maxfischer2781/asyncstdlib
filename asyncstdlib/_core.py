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
    TypeVar,
)
from types import TracebackType

from ._typing import AsyncContextManager, AnyIterable, T


S = TypeVar("S")


class _BorrowedAsyncIterator(AsyncGenerator[T, S]):
    """
    Borrowed async iterator/generator, preventing to ``aclose`` the ``iterable``
    """

    # adding special methods such as `__aiter__` as `__slots__` allows to set them
    # on the instance: the interpreter expects *descriptors* not methods, and
    # `__slots__` are descriptors just like methods.
    __slots__ = "__wrapped__", "__aiter__", "__anext__", "asend", "athrow"

    # Type checker does not understand `__slot__` definitions
    __aiter__: Callable[[Any], AsyncGenerator[T, S]]
    __anext__: Callable[[Any], Awaitable[T]]
    asend: Any
    athrow: Any

    def __init__(self, iterator: Union[AsyncIterator[T], AsyncGenerator[T, S]]):
        self.__wrapped__ = iterator
        # iterator.__aiter__ is likely to return iterator (e.g. for async def: yield)
        # We wrap it in a separate async iterator/generator to hide its __aiter__.
        try:
            wrapped_iterator: AsyncGenerator[T, S] = self._wrapped_iterator(iterator)
            self.__anext__ = iterator.__anext__  # type: ignore
            self.__aiter__ = wrapped_iterator.__aiter__  # type: ignore
        except (AttributeError, TypeError):
            raise TypeError(
                "borrowing requires an async iterator "
                + f"with __aiter__ and __anext__ method, got {type(iterator).__name__}"
            ) from None
        self.__anext__ = wrapped_iterator.__anext__  # type: ignore
        # Our wrapper cannot pass on asend/athrow without getting much heavier.
        # Since interleaving anext/asend/athrow is not allowed, and the wrapper holds
        # no internal state other than the iterator, circumventing it should be fine.
        if hasattr(iterator, "asend"):
            self.asend = iterator.asend  # type: ignore
        if hasattr(iterator, "athrow"):
            self.athrow = iterator.athrow  # type: ignore

    # Py3.6 compatibility
    # Use ``(item async for item in iterator)`` inside
    # ``__init__`` when no longer needed.
    @staticmethod
    async def _wrapped_iterator(
        iterator: Union[AsyncIterator[T], AsyncGenerator[T, S]]
    ) -> AsyncGenerator[T, S]:
        async for item in iterator:
            yield item

    def __repr__(self):
        return f"<asyncstdlib.borrow of {self.__wrapped__!r} at 0x{(id(self)):x}>"

    async def _aclose_wrapper(self):
        wrapper_iterator = self.__aiter__()
        # allow closing the intermediate wrapper
        # this prevents a resource warning if the wrapper is GC'd
        # the underlying iterator is NOT affected by this
        await wrapper_iterator.aclose()
        # disable direct asend/athrow to the underlying iterator
        if hasattr(self, "asend"):
            self.asend = wrapper_iterator.asend
        if hasattr(self, "athrow"):
            self.athrow = wrapper_iterator.athrow

    def aclose(self):
        return self._aclose_wrapper()


class _ScopedAsyncIterator(_BorrowedAsyncIterator[T, S]):
    __slots__ = ()

    def __repr__(self):
        return f"<asyncstdlib.scoped_iter of {self.__wrapped__!r} at 0x{(id(self)):x}>"

    async def aclose(self):
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

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._borrowed_iter._aclose_wrapper()  # type: ignore
        await self._iterator.aclose()  # type: ignore
        return False

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self._iterator!r} at 0x{(id(self)):x}>"


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


def scoped_iter(iterable: AnyIterable[T]):
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
            async with scoped_iter(iterable) as async_iter:
                # ... safely pass it on without it being closed ...
                async for item in a.isclice(async_iter, leading):
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
        from .contextlib import nullcontext

        return nullcontext(iterator)
    return _ScopedAsyncIteratorContext(iterator)


async def _aiter_sync(iterable: Iterable[T]) -> AsyncIterator[T]:
    """Helper to provide an async iterator for a regular iterable"""
    for item in iterable:
        yield item


def borrow(iterator: AsyncIterator[T]) -> _BorrowedAsyncIterator[T, None]:
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
    return _BorrowedAsyncIterator(iterator)


def awaitify(
    function: Union[Callable[..., T], Callable[..., Awaitable[T]]]
) -> Callable[..., Awaitable[T]]:
    """Ensure that ``function`` can be used in ``await`` expressions"""
    if iscoroutinefunction(function):
        return function  # type: ignore
    else:
        return Awaitify(function)


class Awaitify(Generic[T]):
    """Helper to peek at the return value of ``function`` and make it ``async``"""

    __slots__ = "__wrapped__", "_async_call"

    def __init__(self, function: Union[Callable[..., T], Callable[..., Awaitable[T]]]):
        self.__wrapped__ = function
        self._async_call: Optional[Callable[..., Awaitable[T]]] = None

    def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[T]:
        async_call = self._async_call
        if async_call is None:
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
