from typing import (
    TypeVar,
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Generic,
    NamedTuple,
    overload,
    Protocol,
)
from types import CoroutineType
from typing_extensions import ParamSpec, Concatenate

from ._typing import AC, TypedDict

class CacheInfo(NamedTuple):
    hits: int
    misses: int
    maxsize: int | None
    currsize: int

class CacheParameters(TypedDict):
    maxsize: int | None
    typed: bool

R = TypeVar("R")
P = ParamSpec("P")
S = TypeVar("S")
S2 = TypeVar("S2")

class LRUAsyncCallable(Protocol[AC]):
    __slots__: tuple[str, ...]
    __call__: AC
    @overload
    def __get__(
        self: LRUAsyncCallable[AC], instance: None, owner: type | None = ...
    ) -> LRUAsyncCallable[AC]: ...
    @overload
    def __get__(
        self: LRUAsyncCallable[Callable[Concatenate[S, P], Coroutine[Any, Any, R]]],
        instance: S,
        owner: type | None = ...,
    ) -> LRUAsyncBoundCallable[S, P, R]: ...
    @overload
    def __get__(
        self: LRUAsyncCallable[Callable[Concatenate[S, P], CoroutineType[Any, Any, R]]],
        instance: S,
        owner: type | None = ...,
    ) -> LRUAsyncBoundCallable[S, P, R]: ...
    @overload
    def __get__(
        self: LRUAsyncCallable[Callable[Concatenate[S, P], Awaitable[R]]],
        instance: S,
        owner: type | None = ...,
    ) -> LRUAsyncBoundCallable[S, P, R]: ...
    @property
    def __wrapped__(self) -> AC: ...
    def cache_parameters(self) -> CacheParameters: ...
    def cache_info(self) -> CacheInfo: ...
    def cache_clear(self) -> None: ...
    def cache_discard(self, *args: Any, **kwargs: Any) -> None: ...

class LRUAsyncBoundCallable(Generic[S, P, R]):
    __slots__: tuple[str, ...]
    __self__: S
    __call__: Callable[P, Awaitable[R]]
    @overload
    def __get__(
        self, instance: None, owner: type | None = ...
    ) -> LRUAsyncBoundCallable[S, P, R]: ...
    @overload
    def __get__(
        self, instance: S2, owner: type | None = ...
    ) -> LRUAsyncBoundCallable[S2, P, R]: ...
    def __init__(
        self,
        lru: LRUAsyncCallable[Callable[Concatenate[S, P], Awaitable[R]]],
        __self__: S,
    ) -> None: ...
    @property
    def __wrapped__(self) -> Callable[Concatenate[S, P], Awaitable[R]]: ...
    @property
    def __func__(
        self,
    ) -> LRUAsyncCallable[Callable[Concatenate[S, P], Awaitable[R]]]: ...
    def cache_parameters(self) -> CacheParameters: ...
    def cache_info(self) -> CacheInfo: ...
    def cache_clear(self) -> None: ...
    def cache_discard(self, *args: Any, **kwargs: Any) -> None: ...

@overload
def lru_cache(maxsize: AC, typed: bool = ...) -> LRUAsyncCallable[AC]: ...
@overload
def lru_cache(
    maxsize: int | None = ..., typed: bool = ...
) -> Callable[[AC], LRUAsyncCallable[AC]]: ...
