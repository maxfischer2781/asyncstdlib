from typing import (
    Callable,
    Coroutine,
    Iterable,
    AsyncIterator,
    TypeVar,
    Awaitable,
    Deque,
    Tuple,
    Any,
)
from functools import wraps
from collections import deque


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
                if not isinstance(event, PingPong):  # pragma: no cover
                    raise RuntimeError(
                        f"test case {test_case} yielded an unexpected event {event}"
                    )
        except StopIteration as e:
            result = e.args[0] if e.args else None
        return result

    return run_sync


class Schedule:
    """Signal to the event loop to adopt and run a new coroutine"""

    def __init__(self, *coros: Coroutine):
        self.coros = coros

    def __await__(self):
        yield self


class Switch:
    """Signal to the event loop to run another coroutine"""

    def __await__(self):
        yield self


def multi_sync(test_case: Callable[..., Coroutine]):
    """
    Mark an ``async def`` test case to be run synchronously with chicldren

    This emulates a primitive "event loop" which only responds
    to the :py:class:`PingPong`, :py:class:`Schedule` and :py:class:`Switch`.
    """

    @wraps(test_case)
    def run_sync(*args, **kwargs):
        run_queue: Deque[Tuple[Coroutine, Any]] = deque()
        run_queue.append((test_case(*args, **kwargs), None))
        while run_queue:
            coro, event = run_queue.popleft()
            try:
                event = coro.send(event)
            except StopIteration as e:
                result = e.args[0] if e.args else None
                assert result is None
            else:
                if isinstance(event, PingPong):
                    run_queue.appendleft((coro, event))
                elif isinstance(event, Schedule):
                    run_queue.extend((new_coro, None) for new_coro in event.coros)
                    run_queue.append((coro, event))
                elif isinstance(event, Switch):
                    run_queue.append((coro, event))
                else:  # pragma: no cover
                    raise RuntimeError(
                        f"test case {test_case} yielded an unexpected event {event}"
                    )

    return run_sync
