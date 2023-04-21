from ._typing import AC, Protocol, R as R, TypedDict
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Hashable,
    NamedTuple,
    Optional,
    Tuple,
    Union,
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
        self: LRUAsyncCallable[Callable[..., Awaitable[R]]],
        instance: None,
        owner: Optional[type],
    ) -> LRUAsyncCallable[Callable[..., Awaitable[R]]]: ...
    @overload
    def __get__(
        self: LRUAsyncCallable[Callable[..., Awaitable[R]]],
        instance: Any,
        owner: Optional[type],
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
    def __init__(self, lru: LRUAsyncCallable[AC], __self__: object) -> None: ...
    @property
    def __wrapped__(self) -> AC: ...
    @property
    def __func__(self) -> LRUAsyncCallable[AC]: ...
    def cache_parameters(self) -> CacheParameters: ...
    def cache_info(self) -> CacheInfo: ...
    def cache_clear(self) -> None: ...
    def cache_discard(self, *args: Any, **kwargs: Any) -> None: ...
    def __getattr__(self, name: str) -> Any: ...

@overload
def lru_cache(maxsize: AC, typed: bool = ...) -> LRUAsyncCallable[AC]: ...
@overload
def lru_cache(
    maxsize: Optional[int] = ..., typed: bool = ...
) -> Callable[[AC], LRUAsyncCallable[AC]]: ...