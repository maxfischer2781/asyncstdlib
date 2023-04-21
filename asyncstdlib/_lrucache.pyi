from ._typing import AC, Protocol, R as R, TypedDict
from typing import (
    Any,
    Awaitable,
    Callable,
    NamedTuple,
    Optional,
    overload,
)

class CacheInfo(NamedTuple):
    hits: int
    misses: int
    maxsize: Optional[int]
    currsize: int

class CacheParameters(TypedDict):
    maxsize: Optional[int]
    typed: bool

class LRUAsyncCallable(Protocol[AC]):
    __call__: AC
    @overload
    def __get__(
        self: LRUAsyncCallable[AC],
        instance: None,
        owner: Optional[type] = ...,
    ) -> LRUAsyncCallable[AC]: ...
    @overload
    def __get__(
        self: LRUAsyncCallable[Callable[..., Awaitable[R]]],
        instance: object,
        owner: Optional[type] = ...,
    ) -> LRUAsyncBoundCallable[Callable[..., Awaitable[R]]]: ...
    @property
    def __wrapped__(self) -> AC: ...
    def cache_parameters(self) -> CacheParameters: ...
    def cache_info(self) -> CacheInfo: ...
    def cache_clear(self) -> None: ...
    def cache_discard(self, *args: Any, **kwargs: Any) -> None: ...

class LRUAsyncBoundCallable(LRUAsyncCallable[AC]):
    __self__: object
    __call__: AC
    def __get__(
        self: LRUAsyncBoundCallable[AC],
        instance: Any,
        owner: Optional[type] = ...,
    ) -> LRUAsyncBoundCallable[AC]: ...
    def __init__(self, lru: LRUAsyncCallable[AC], __self__: object) -> None: ...
    @property
    def __wrapped__(self) -> AC: ...
    @property
    def __func__(self) -> LRUAsyncCallable[AC]: ...

@overload
def lru_cache(maxsize: AC, typed: bool = ...) -> LRUAsyncCallable[AC]: ...
@overload
def lru_cache(
    maxsize: Optional[int] = ..., typed: bool = ...
) -> Callable[[AC], LRUAsyncCallable[AC]]: ...
