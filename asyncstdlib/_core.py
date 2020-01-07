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

T = TypeVar("T")


AnyIterable = Union[Iterable[T], AsyncIterable[T]]


class Sentinel:
    """Placeholder with configurable ``repr``"""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


__ITER_SENTINEL = Sentinel("<no default>")


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

    async def __aenter__(self) -> Tuple[AsyncIterator[T], ...]:
        assert self._iterators is None, f"{self.__class__.__name__} is not re-entrant"
        self._iterators = (*(aiter(it) for it in self._iterables),)
        return self._iterators

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for iterable, iterator in zip(self._iterables, self._iterators):
            await close_temporary(iterator, iterable)
        return False


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

    def __call__(self, *args, **kwargs) -> Awaitable[T]:
        async_call = self._async_call
        if async_call is None:
            value = self.__wrapped__(*args, **kwargs)
            if isinstance(value, Awaitable):
                self._async_call = self.__wrapped__
                return value
            else:
                self._async_call = force_async(self.__wrapped__)
                return await_value(value)
        else:
            return async_call(*args, **kwargs)


async def await_value(value: T) -> T:
    return value


def force_async(call: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    async def async_wrapped(*args, **kwargs):
        return call(*args, **kwargs)

    return async_wrapped
