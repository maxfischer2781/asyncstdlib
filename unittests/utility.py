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
from random import randint


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

    If a single argument is given, this specifies how many
    turns should be skipped. The default corresponds to `0`.
    If two arguments are given, this is interpreted as an
    inclusive interval to randomly select the skip count.
    """

    def __init__(self, skip: int = 0, limit: int = 0, /) -> None:
        if limit <= 0:
            self._idle_count = skip
        else:
            self._idle_count = randint(skip, limit)

    def __await__(self):
        yield self
        for _ in range(self._idle_count):
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


def sync(test_case: Callable[..., Coroutine[None, Any, Any]], /) -> Callable[..., None]:
    """
    Mark an ``async def`` test case to be run synchronously with children

    This provides a primitive "event loop" which only responds
    to :py:class:`Schedule`, :py:class:`Switch` and :py:class:`Lock`.

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
                if isinstance(event, Schedule):
                    run_queue.extend((new_coro, None) for new_coro in event.coros)
                    run_queue.append((coro, event))
                elif isinstance(event, Switch):
                    run_queue.append((coro, event))
                else:  # pragma: no cover
                    raise RuntimeError(
                        f"test case {test_case} yielded an unexpected event {event}"
                    )

    return run_sync
