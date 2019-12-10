from typing import TypeVar, Generic, AsyncGenerator, Callable
from typing_extensions import Protocol, AsyncContextManager
from functools import wraps


class ACloseable(Protocol):
    async def aclose(self):
        """Asynchronously close this object"""


T = TypeVar("T")
AC = TypeVar("AC", bound=ACloseable)


def contextmanager(
    func: Callable[..., AsyncGenerator[T, None]]
) -> Callable[..., AsyncContextManager[T]]:
    """
    Create an asynchronous context manager out of an asynchronous generator function

    This is intended as a decorator for an asynchronous generator function.
    The asynchronous generator should ``yield`` once, at which point the body of the
    context manager executes. If ``yield`` provides a value, this becomes the value
    of the context in the block.

    .. code-block:: python3

        @contextmanager
        async def Context(*args, **kwargs):
            # __aenter__
            yield  # context value
            # __aexit__

    Note that if an exception ends the context block, it gets re-raised at the ``yield``
    inside the asynchronous generator (via :py:meth:`~agen.athrow`). In order to handle
    this exception, the ``yield`` should be wrapped in a ``try`` statement.
    """

    @wraps(func)
    def helper(*args, **kwds):
        return _AsyncGeneratorContextManager(func, args, kwds)

    return helper


class _AsyncGeneratorContextManager:
    def __init__(self, func, args, kwds):
        self.gen = func(*args, **kwds)
        self.__doc__ = getattr(func, "__doc__", type(self).__doc__)

    async def __aenter__(self):
        try:
            return await self.gen.__anext__()
        except StopAsyncIteration:
            raise RuntimeError("generator did not yield to __aenter__") from None

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            try:
                await self.gen.__anext__()
            except StopAsyncIteration:
                return
            else:
                raise RuntimeError("generator did not stop after __aexit__")
        else:
            try:
                await self.gen.athrow(exc_type, exc_val, exc_tb)
            except StopAsyncIteration as exc:
                return exc is not exc_tb
            except RuntimeError as exc:
                if exc is exc_val:
                    return False
                # Handle promotion of unhandled Stop[Async]Iteration to RuntimeError
                if isinstance(exc_val, (StopIteration, StopAsyncIteration)):
                    if exc.__cause__ is exc_val:
                        return False
                raise
            except exc_type as exc:
                if exc is not exc_val:
                    raise
            else:
                raise RuntimeError("generator did not stop after throw() in __aexit__")


class closing(Generic[AC]):
    """
    Create an :term:`asynchronous context manager` to ``aclose`` some ``thing`` on exit

    Once entered, the context manager guarantees to ``await thing.aclose()``
    at the end of its block. This is useful for safe cleanup even if errors
    occur.

    Use :py:class:`~.closing` for objects that need reliable cleanup but do not support
    the context manager protocol. For example, it is advisable to prompty clean up any
    :term:`asynchronous iterator` that holds resources:

    .. code-block:: python3

        import asyncstdlib as a

        async with a.closing(a.iter(something)) as async_iter:
            async for element in async_iter:
                ...
    """

    def __init__(self, thing: AC):
        self.thing = thing

    async def __aenter__(self) -> AC:
        return self.thing

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.thing.aclose()


class nullcontext(Generic[T]):
    """
    Create an :term:`asynchronous context manager` that only returns ``enter_result``

    Intended as a neutral element, a :py:class:`~.nullcontext` serves as a
    placeholder where an async context manager is semantically required
    but not meaningfull. This allows for an optional async context manager with
    a default :py:class:`~.nullcontext`, or to prevent closing of an existing
    context manager in an ``async with`` statement.

    .. code-block:: python3

        async def safe_fetch(source):
            if not isinstance(source, AsyncIterator):
                # use a context manager if required ...
                acm = a.closing(iter(source))
            else:
                # ... or a neutral placeholder
                acm = a.nullcontext(source)
            async with acm as async_iter:
                ...
    """

    def __init__(self, enter_result: T = None):
        self.enter_result = enter_result

    async def __aenter__(self) -> T:
        return self.enter_result

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
