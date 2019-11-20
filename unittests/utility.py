from typing import Callable, Coroutine, Iterable, AsyncIterator, TypeVar
from functools import wraps


T = TypeVar("T")


async def asyncify(iterable: Iterable[T]) -> AsyncIterator[T]:
    """Convert an iterable to async iterable"""
    for value in iterable:
        yield value


class UnfinishedTest(RuntimeError):
    """A test did never finish"""

    def __init__(self, test_case):
        self.test_case = test_case
        super().__init__(
            "Test case %r did not finish" % getattr(test_case, "__name__", test_case)
        )


def sync(test_case: Callable[..., Coroutine]):
    """
    Mark an ``async def`` test case to be run synchronously

    This emulates a primitive "event loop" which does not
    respond to any events.
    """

    @wraps(test_case)
    def run_sync(*args, **kwargs):
        coro = test_case(*args, **kwargs)
        try:
            event = coro.send(None)
        except StopIteration as e:
            result = e.args[0] if e.args else None
        else:
            if event:
                raise RuntimeError(f"test case {test_case} yielded an event")
            raise UnfinishedTest(test_case)
        return result

    return run_sync
