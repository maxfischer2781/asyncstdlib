from typing import Union, AsyncIterator, TypeVar, AsyncContextManager, Optional, AsyncGenerator

from ._core import AnyIterable, aiter
from .contextlib import nullcontext


T = TypeVar('T')
S = TypeVar('S')


class AsyncIteratorBorrow(AsyncGenerator[T, S]):
    """
    Borrowed async iterator/generator, preventing to ``aclose`` the ``iterable``
    """

    __slots__ = '__wrapped__', '__aiter__', '__anext__', 'asend', 'athrow'

    def __init__(self, iterator: Union[AsyncIterator[T], AsyncGenerator[T, S]]):
        self.__wrapped__ = iterator
        try:
            wrapped_iterator: AsyncGenerator[T, S] = (item async for item in iterator)
            self.__anext__ = iterator.__anext__  # argument may not be an iterable!
        except (AttributeError, TypeError):
            raise TypeError(
                'borrowing requires an async iterator ' +
                f'with __aiter__ and __anext__ method, got {type(iterator).__name__}'
            ) from None
        self.__aiter__ = wrapped_iterator.__aiter__
        if hasattr(iterator, 'asend'):
            self.asend = iterator.asend
        if hasattr(iterator, 'athrow'):
            self.athrow = iterator.athrow

    async def aclose(self):
        pass


class AsyncIteratorContext(AsyncContextManager[AsyncIterator[T]]):

    __slots__ = '__wrapped__', '_iterator'

    def __init__(self, iterable: AnyIterable[T]):
        self._iterator: Optional[AsyncIterator[T]] = aiter(iterable)

    async def __aenter__(self) -> AsyncIterator[T]:
        return AsyncIteratorBorrow(self._iterator)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._iterator.aclose()
        return False


def borrow(iterator: AsyncIterator[T]) -> AsyncIteratorBorrow[T, None]:
    """
    Borrow an async iterator, preventing to ``aclose`` it

    When :term:`borrowing` an async iterator, the original owner assures
    to close the iterator as needed. In turn, the borrowed iterator does
    not allow closing the underlying iterator.

    The borrowed iterator supports :py:meth:`~agen.asend` and
    :py:meth:`~agen.athrow` if the underlying iterator supports them as well;
    this allows borrowing either an :py:class:`~collections.abc.AsyncIterator`
    or :py:class:`~collections.abc.AsyncGenerator`. Regardless of iterator,
    :py:meth:`~agen.aclose` is always provided and does nothing.

    .. seealso:: Use :py:func:`~.scoped_iter` to ensure an (async) iterable
                 is eventually closed and only borrowed until then.
    """
    if isinstance(iterator, AsyncIteratorBorrow):
        return iterator
    return AsyncIteratorBorrow(iterator)


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

    Nested scoping of the same iterator is safe: inner scopes automatically
    forfeit closing the iterator in favour of the outermost scope.
    """
    # The iterable has already been borrowed.
    # Someone else takes care of it.
    if isinstance(iterable, AsyncIteratorBorrow):
        return nullcontext(iterable)
    iterator = aiter(iterable)
    # The iterable cannot be closed.
    # We do not need to take care of it.
    if not hasattr(iterator, 'aclose'):
        return nullcontext(iterator)
    return AsyncIteratorContext(iterator)

