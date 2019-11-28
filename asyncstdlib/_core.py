from typing import TypeVar, AsyncIterator, Iterable, AsyncIterable, Union

from ._utility import public_module

T = TypeVar('T')


AnyIterable = Union[Iterable[T], AsyncIterable[T]]


@public_module('asyncstdlib.builtins')
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