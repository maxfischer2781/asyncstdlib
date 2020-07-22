from typing import (
    Union,
    AsyncIterator,
    TypeVar,
    AsyncGenerator,
)
from typing_extensions import AsyncContextManager

from ._core import AnyIterable, aiter
from .contextlib import nullcontext


T = TypeVar("T")
S = TypeVar("S")


class _BorrowedAsyncIterator(AsyncGenerator[T, S]):
    """
    Borrowed async iterator/generator, preventing to ``aclose`` the ``iterable``
    """

    __slots__ = "__wrapped__", "__aiter__", "__anext__", "asend", "athrow"

    def __init__(self, iterator: Union[AsyncIterator[T], AsyncGenerator[T, S]]):
        self.__wrapped__ = iterator
        # iterator.__aiter__ is likely to return iterator (e.g. for async def: yield)
        # We wrap it in a separate async iterator/generator to hide its __aiter__.
        try:
            wrapped_iterator: AsyncGenerator[T, S] = self._wrapped_iterator(iterator)
            self.__anext__ = iterator.__anext__  # argument must be an async iterable!
        except (AttributeError, TypeError):
            raise TypeError(
                "borrowing requires an async iterator "
                + f"with __aiter__ and __anext__ method, got {type(iterator).__name__}"
            ) from None
        self.__aiter__ = wrapped_iterator.__aiter__
        self.__anext__ = wrapped_iterator.__anext__
        # Our wrapper cannot pass on asend/athrow without getting much heavier.
        # Since interleaving anext/asend/athrow is not allowed, and the wrapper holds
        # no internal state other than the iterator, circumventing it should be fine.
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
        self._borrowed_iter = None

    async def __aenter__(self) -> AsyncIterator[T]:
        if self._borrowed_iter is not None:
            raise RuntimeError("scoped_iter is not re-entrant")
        borrowed_iter = self._borrowed_iter = _ScopedAsyncIterator(self._iterator)
        return borrowed_iter

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._borrowed_iter._aclose_wrapper()
        await self._iterator.aclose()
        return False

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self._iterator!r} at 0x{(id(self)):x}>"


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
        return nullcontext(iterator)
    return _ScopedAsyncIteratorContext(iterator)
