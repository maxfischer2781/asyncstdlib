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


def sync(test_case: Callable[..., Coroutine[T, Any, Any]]) -> Callable[..., T]:
    """
    Mark an ``async def`` test case to be run synchronously

    This emulates a primitive "event loop" which only responds
    to the :py:class:`PingPong` by sending it back.
    """

    @wraps(test_case)
    def run_sync(*args: Any, **kwargs: Any) -> T:
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

    def __init__(self, *coros: Coroutine[Any, Any, Any]):
        self.coros = coros

    def __await__(self):
        yield self


class Switch:
    """Signal to the event loop to run another coroutine"""

    def __await__(self):
        yield self


class Lock:
    def __init__(self):
        self._owned = False
        self._waiting: list[object] = []

    async def __aenter__(self):
        if self._owned:
            # wait until it is our turn to take the lock
            token = object()
            self._waiting.append(token)
            while self._owned or self._waiting[0] is not token:
                await Switch()
            # take the lock and remove our wait claim
            self._owned = True
            self._waiting.pop(0)
        self._owned = True

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        self._owned = False


def multi_sync(test_case: Callable[..., Coroutine[T, Any, Any]]) -> Callable[..., T]:
    """
    Mark an ``async def`` test case to be run synchronously with children

    This emulates a primitive "event loop" which only responds
    to the :py:class:`PingPong`, :py:class:`Schedule`, :py:class:`Switch`
    and :py:class:`Lock`.
    """

    @wraps(test_case)
    def run_sync(*args: Any, **kwargs: Any):
        run_queue: Deque[Tuple[Coroutine[Any, Any, Any], Any]] = deque()
        run_queue.append((test_case(*args, **kwargs), None))
        while run_queue:
            coro, event = run_queue.popleft()
            try:
                event = coro.send(event)
            except StopIteration as e:
                result = e.args[0] if e.args else None
                assert result is None, f"got '{result!r}' expected 'None'"
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
