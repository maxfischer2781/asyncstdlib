from typing import Any, AsyncContextManager, Awaitable, Callable, Generic, overload

from ._typing import T, T1, T2, AC, AnyIterable, R

from ._lrucache import (
    LRUAsyncCallable as LRUAsyncCallable,
    LRUAsyncBoundCallable as LRUAsyncBoundCallable,
    lru_cache as lru_cache,
)

def cache(user_function: AC) -> LRUAsyncCallable[AC]: ...

class CachedProperty(Generic[T, R]):
    def __init__(
        self,
        getter: Callable[[T], Awaitable[R]],
        lock_type: type[AsyncContextManager[Any]] = ...,
    ) -> None: ...
    def __set_name__(self, owner: Any, name: str) -> None: ...
    @overload
    def __get__(self, instance: None, owner: type[Any]) -> "CachedProperty[T, R]": ...
    @overload
    def __get__(self, instance: T, owner: type | None) -> Awaitable[R]: ...
    # __set__ is not defined at runtime, but you are allowed to replace the cached value
    def __set__(self, instance: T, value: R) -> None: ...  # type: ignore[misc]  # pyright: ignore[reportGeneralTypeIssues]
    # __del__ is not defined at runtime, but you are allowed to delete the cached value
    def __del__(self, instance: T) -> None: ...

@overload
def cached_property(getter: Callable[[T], Awaitable[R]], /) -> CachedProperty[T, R]: ...
@overload
def cached_property(
    asynccontextmanager_type: type[AsyncContextManager[Any]], /
) -> Callable[[Callable[[T], Awaitable[R]]], CachedProperty[T, R]]: ...
@overload
async def reduce(
    function: Callable[[T1, T2], T1], iterable: AnyIterable[T2], initial: T1
) -> T1: ...
@overload
async def reduce(function: Callable[[T, T], T], iterable: AnyIterable[T]) -> T: ...
