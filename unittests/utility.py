from typing import (
    Callable,
    Coroutine,
    Generator,
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
    """
    Convert an iterable into an async iterable

    This is intended to sequence literals like lists to `async` iterators
    in order to force usage of `async` code paths. There is no functional
    or other advantage otherwise.
    """
    for value in iterable:
        yield value


def awaitify(call: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    """
    Convert a callable (`foo()`) into an async callable (`await foo()`)

    This is intended to convert `lambda` expressions to `async` functions
    in order to force usage of `async` code paths. There is no functional
    or other advantage otherwise.
    """

    async def await_wrapper(*args: Any, **kwargs: Any) -> T:
        return call(*args, **kwargs)

    return await_wrapper


class PingPong:
    """
    Signal to the event loop which gets returned unchanged

    The coroutine yields to the event loop but is resumed
    immediately, without running others in the meantime.
    This is mainly useful for ensuring the event loop is used.
    """

    def __await__(self) -> "Generator[PingPong, Any, Any]":
        return (yield self)


async def inside_loop() -> bool:
    """Test whether there is an active event loop available"""
    signal = PingPong()
    return await signal is signal


def sync(test_case: Callable[..., Coroutine[None, Any, Any]]) -> Callable[..., None]:
    """
    Mark an ``async def`` test case to be run synchronously

    This emulates a primitive "event loop" which only responds
    to the :py:class:`PingPong` by sending it back. This loop
    is appropriate for tests that do not check concurrency.
    """

    @wraps(test_case)
    def run_sync(*args: Any, **kwargs: Any) -> None:
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
            assert result is None, f"got '{result!r}' expected 'None'"
        return result

    return run_sync


class Schedule:
    r"""
    Signal to the event loop to adopt and run new coroutines

    :param coros: The coroutines to start running

    In order to communicate with the event loop and start the coroutines,
    the :py:class:`Schedule` must be `await`\ ed.
    """

    def __init__(self, *coros: Coroutine[Any, Any, Any]):
        self.coros = coros

    def __await__(self):
        yield self


class Switch:
    """
    Signal to the event loop to run another coroutine

    Pauses the coroutine but immediately continues after
    all other runnable coroutines of the event loop.
    This is similar to the common ``sleep(0)`` function
    of regular event loop frameworks.
    """

    def __await__(self):
        yield self


class Lock:
    """Simple lock for exclusive access"""

    def __init__(self):
        self._owned = False
        self._waiting: list[object] = []

    async def __aenter__(self):
        if self._owned:
            # wait until it is our turn to take the lock
            token = object()
            self._waiting.append(token)
            # a spin-lock should be fine since tests are short anyways
            while self._owned or self._waiting[0] is not token:
                await Switch()
            # we will take the lock now, remove our wait claim
            self._waiting.pop(0)
        self._owned = True

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        self._owned = False


def multi_sync(
    test_case: Callable[..., Coroutine[None, Any, Any]], /
) -> Callable[..., None]:
    """
    Mark an ``async def`` test case to be run synchronously with children

    This provides a primitive "event loop" which only responds
    to the :py:class:`PingPong`, :py:class:`Schedule`, :py:class:`Switch`
    and :py:class:`Lock`. This loop is appropriate for tests that need
    to check concurrency.

    It should be applied as a decorator on an ``async def`` function, which
    is then turned into a synchronous callable that will run the ``async def``
    function and all tasks it spawns.
    Other decorators, most prominently :py:func:`pytest.mark.parametrize`,
    can be applied around it.
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
