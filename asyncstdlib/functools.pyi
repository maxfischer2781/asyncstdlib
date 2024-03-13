from typing import Any, Awaitable, Callable, Generic, overload

from ._typing import T, T1, T2, AC, AnyIterable

from ._lrucache import (
    LRUAsyncCallable as LRUAsyncCallable,
    LRUAsyncBoundCallable as LRUAsyncBoundCallable,
    lru_cache as lru_cache,
)

def cache(user_function: AC) -> LRUAsyncCallable[AC]: ...

class cached_property(Generic[T]):
    def __init__(self, getter: Callable[[Any], Awaitable[T]]) -> None: ...
    def __set_name__(self, owner: Any, name: str) -> None: ...
    @overload
    def __get__(self, instance: None, owner: type) -> "cached_property[T]": ...
    @overload
    def __get__(self, instance: object, owner: type | None) -> Awaitable[T]: ...

@overload
async def reduce(
    function: Callable[[T1, T2], T1], iterable: AnyIterable[T2], initial: T1
) -> T1: ...
@overload
async def reduce(function: Callable[[T, T], T], iterable: AnyIterable[T]) -> T: ...
