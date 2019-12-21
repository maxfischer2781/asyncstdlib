from inspect import iscoroutinefunction
from typing import (
    TypeVar,
    AsyncIterator,
    Iterable,
    AsyncIterable,
    Union,
    Generic,
    Optional,
    Tuple,
    Iterator,
    Awaitable,
    Callable,
)

from ._utility import public_module

T = TypeVar("T")


AnyIterable = Union[Iterable[T], AsyncIterable[T]]


class Sentinel:
    """Placeholder with configurable ``repr``"""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


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


async def close_temporary(
    iterator: AsyncIterator,
    source: Union[AsyncIterator, AsyncIterable, Iterator, Iterable],
):
    """Close an ``iterator`` created from ``source`` if it is a separate object"""
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
        assert self._iterators is None, f"{self.__class__.__name__} is not re-entrant"
        self._iterators = (*(iter(it) for it in self._iterables),)
        return self._iterators

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for iterable, iterator in zip(self._iterables, self._iterators):
            await close_temporary(iterator, iterable)
        return False


def awaitify(
    function: Union[Callable[..., T], Callable[..., Awaitable[T]]]
) -> Callable[..., Awaitable[T]]:
    if iscoroutinefunction(function):
        return function
    else:
        return Awaitify(function)


class Awaitify(Generic[T]):
    __slots__ = "function", "is_async"

    def __init__(self, function: Union[Callable[..., T], Callable[..., Awaitable[T]]]):
        self.function = function
        self.is_async = None

    def __call__(self, *args, **kwargs) -> Awaitable[T]:
        value = self.function(*args, **kwargs)
        if self.is_async is None:
            if isinstance(value, Awaitable):
                self.is_async = True
                return value
            else:
                self.is_async = False
                return await_value(value)
        elif self.is_async:
            return value
        else:
            return await_value(value)


async def await_value(value: T) -> T:
    return value
