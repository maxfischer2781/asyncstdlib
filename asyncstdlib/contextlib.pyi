from typing import (
    TypeVar,
    Generic,
    AsyncGenerator,
    Callable,
    Optional,
    Any,
    Awaitable,
    overload,
    AsyncContextManager,
)
from typing_extensions import ParamSpec, Self
from types import TracebackType
from abc import ABCMeta

from ._typing import AClose, ContextManager, AC, T, R

AnyContextManager = AsyncContextManager[T] | ContextManager[T]

class ContextDecorator(AsyncContextManager[T], metaclass=ABCMeta):
    """
    Base class for an async context manager useable as a decorator as well

    Inheriting from this class adds the scaffolding to automatically enter
    an async context manager on awaiting any callable decorated with it:

    .. code:: python3

        class DecoratorAndContext(AsyncContextDecorator):
            async def __aenter__(self) -> Any:
                print("entering", self)

            async def __aexit__(self, *exc):
                print("exiting", self)

        @DecoratorAndContext()
        async def func():
            # DecoratorAndContext has been entered already
            print("running some function...")
            # DecoratorAndContext will be exited immediately

    The context manager can still be used regularly in `async with` statements.

    Since functions are decorated with an existing context manager instance,
    the same instance is entered and exited on every call. If the context is
    not safe to be entered multiple times or even concurrently the subclass
    should implement the method `_recreate_cm(:Self) -> Self` to create a copy.
    """

    __slots__ = ()

    def _recreate_cm(self: Self) -> Self: ...
    def __call__(self, func: AC, /) -> AC: ...

P = ParamSpec("P")

def contextmanager(
    func: Callable[P, AsyncGenerator[T, None]]
) -> Callable[P, ContextDecorator[T]]: ...

class closing(Generic[AClose]):
    def __init__(self, thing: AClose) -> None: ...
    async def __aenter__(self: Self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool: ...

class nullcontext(AsyncContextManager[T]):
    enter_result: T

    @overload
    def __init__(self: nullcontext[None], enter_result: None = ...) -> None: ...
    @overload
    def __init__(self: nullcontext[T], enter_result: T) -> None: ...
    async def __aenter__(self: nullcontext[T]) -> T: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool: ...

SE = TypeVar(
    "SE",
    bound=AsyncContextManager[Any]
    | ContextManager[Any]
    | Callable[
        [type[BaseException] | None, BaseException | None, TracebackType | None],
        Optional[bool],
    ]
    | Callable[
        [type[BaseException] | None, BaseException | None, TracebackType | None],
        Awaitable[Optional[bool]],
    ],
)

class ExitStack:
    def __init__(self) -> None: ...
    def pop_all(self: Self) -> Self: ...
    def push(self, exit: SE) -> SE: ...
    def callback(
        self, callback: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> Callable[P, R]: ...
    async def enter_context(self, cm: AnyContextManager[T]) -> T: ...
    async def aclose(self) -> None: ...
    async def __aenter__(self: Self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: TracebackType | None,
    ) -> bool: ...
