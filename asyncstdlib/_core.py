from typing import TypeVar, AsyncIterator, Iterable, AsyncIterable, Union, Generic, Optional, Tuple, Iterator

from ._utility import public_module

T = TypeVar("T")


AnyIterable = Union[Iterable[T], AsyncIterable[T]]


@public_module("asyncstdlib.builtins")
def iter(subject: AnyIterable[T]) -> AsyncIterator[T]:
    """
    An async iterator object yielding elements from ``subject``

    :raises TypeError: if ``subject`` does not support any iteration protocol

    The ``subject`` must support
    the async iteration protocol (the :py:meth:`object.__aiter__` method),
    the regular iteration protocol (the :py:meth:`object.__iter__` method),
    or it must support the sequence protocol (the :py:meth:`object.__getitem__`
    method with integer arguments starting at 0).
    In either case, an async iterator is returned.

    .. note::

        The two-argument form of :py:func:`iter` as ``iter(subject, sentinel)``
        is currently not supported.
    """
    if isinstance(subject, AsyncIterable):
        return subject.__aiter__()
    else:
        return _aiter_sync(subject).__aiter__()


async def _aiter_sync(iterable: Iterable[T]) -> AsyncIterator[T]:
    """Helper to provide an async iterator for a regular iterable"""
    for item in iterable:
        yield item


async def close_temporary(iterator: AsyncIterator, source: Union[AsyncIterator, AsyncIterable, Iterator, Iterable]):
    if iterator is not source:
        try:
            aclose = iterator.aclose()
        except AttributeError:
            pass
        else:
            await aclose


class ScopedIter(Generic[T]):
    """Context manager that provides iterators and cleans up any created ones"""
    def __init__(self, *iterables: AnyIterable[T]):
        self._iterables = iterables
        self._iterators: Optional[Tuple[AsyncIterator[T], ...]] = None

    async def __aenter__(self) -> Tuple[AsyncIterator, ...]:
        assert self._iterators is None, f'{self.__class__.__name__} is not re-entrant'
        self._iterators = (*(iter(it) for it in self._iterables),)
        return self._iterators

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for iterable, iterator in zip(self._iterables, self._iterators):
            await close_temporary(iterator, iterable)
        return False
