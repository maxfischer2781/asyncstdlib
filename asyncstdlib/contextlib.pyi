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

from ._typing import AClose, ContextManager, T, R

AnyContextManager = AsyncContextManager[T] | ContextManager[T]

P = ParamSpec("P")

def contextmanager(
    func: Callable[P, AsyncGenerator[T, None]]
) -> Callable[P, AsyncContextManager[T]]: ...

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
    @overload
    async def __aenter__(self: nullcontext[None]) -> None: ...
    @overload
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
