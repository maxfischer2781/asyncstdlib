from typing import Callable, Coroutine, Iterable, AsyncIterator, TypeVar, Awaitable
from functools import wraps


T = TypeVar("T")


async def asyncify(iterable: Iterable[T]) -> AsyncIterator[T]:
    """Convert an iterable to async iterable"""
    for value in iterable:
        yield value


def awaitify(call: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    async def await_wrapper(*args, **kwargs):
        return call(*args, **kwargs)

    return await_wrapper


class PingPong:
    """Signal to the event loop which gets returned unchanged"""

    def __await__(self):
        return (yield self)


async def inside_loop():
    """Test whether there is an active event loop available"""
    signal = PingPong()
    return await signal is signal


def sync(test_case: Callable[..., Coroutine]):
    """
    Mark an ``async def`` test case to be run synchronously

    This emulates a primitive "event loop" which only responds
    to the :py:class:`PingPong` by sending it back.
    """

    @wraps(test_case)
    def run_sync(*args, **kwargs):
        coro = test_case(*args, **kwargs)
        try:
            event = None
            while True:
                event = coro.send(event)
                if not isinstance(event, PingPong):
                    raise RuntimeError(
                        f"test case {test_case} yielded an unexpected event {event}"
                    )
        except StopIteration as e:
            result = e.args[0] if e.args else None
        return result

    return run_sync
