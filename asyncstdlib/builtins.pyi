from typing import Any, AsyncIterator, Awaitable, Callable, overload
import builtins

from ._typing import ADD, AnyIterable, HK, LT, R, T, T1, T2, T3, T4, T5

@overload
async def anext(iterator: AsyncIterator[T]) -> T: ...
@overload
async def anext(iterator: AsyncIterator[T], default: T) -> T: ...
@overload
def iter(subject: AnyIterable[T]) -> AsyncIterator[T]: ...
@overload
def iter(subject: Callable[[], Awaitable[T]], sentinel: T) -> AsyncIterator[T]: ...
async def all(iterable: AnyIterable[T]) -> bool: ...
async def any(iterable: AnyIterable[T]) -> bool: ...
@overload
def zip(
    __it1: AnyIterable[T1],
    *,
    strict: bool = ...,
) -> AsyncIterator[builtins.tuple[T1]]: ...
@overload
def zip(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    *,
    strict: bool = ...,
) -> AsyncIterator[builtins.tuple[T1, T2]]: ...
@overload
def zip(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    *,
    strict: bool = ...,
) -> AsyncIterator[builtins.tuple[T1, T2, T3]]: ...
@overload
def zip(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    *,
    strict: bool = ...,
) -> AsyncIterator[builtins.tuple[T1, T2, T3, T4]]: ...
@overload
def zip(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    __it5: AnyIterable[T5],
    *,
    strict: bool = ...,
) -> AsyncIterator[builtins.tuple[T1, T2, T3, T4, T5]]: ...
@overload
def zip(
    __it1: AnyIterable[Any],
    __it2: AnyIterable[Any],
    __it3: AnyIterable[Any],
    __it4: AnyIterable[Any],
    __it5: AnyIterable[Any],
    *iterables: AnyIterable[Any],
    strict: bool = ...,
) -> AsyncIterator[builtins.tuple[Any, ...]]: ...
@overload
def map(
    function: Callable[[T1], Awaitable[R]],
    __it1: AnyIterable[T1],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[[T1], R],
    __it1: AnyIterable[T1],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[[T1, T2], Awaitable[R]],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[[T1, T2], R],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[[T1, T2, T3], Awaitable[R]],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[[T1, T2, T3], R],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[[T1, T2, T3, T4], Awaitable[R]],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[[T1, T2, T3, T4], R],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[[T1, T2, T3, T4, T5], Awaitable[R]],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    __it5: AnyIterable[T5],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[[T1, T2, T3, T4, T5], R],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    __it5: AnyIterable[T5],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[..., Awaitable[R]],
    __it1: AnyIterable[Any],
    __it2: AnyIterable[Any],
    __it3: AnyIterable[Any],
    __it4: AnyIterable[Any],
    __it5: AnyIterable[Any],
    *iterable: AnyIterable[Any],
) -> AsyncIterator[R]: ...
@overload
def map(
    function: Callable[..., R],
    __it1: AnyIterable[Any],
    __it2: AnyIterable[Any],
    __it3: AnyIterable[Any],
    __it4: AnyIterable[Any],
    __it5: AnyIterable[Any],
    *iterable: AnyIterable[Any],
) -> AsyncIterator[R]: ...
@overload
async def max(iterable: AnyIterable[LT], *, key: None = ...) -> LT: ...
@overload
async def max(iterable: AnyIterable[LT], *, key: None = ..., default: T) -> LT | T: ...
@overload
async def max(iterable: AnyIterable[T1], *, key: Callable[[T1], LT] = ...) -> T1: ...
@overload
async def max(
    iterable: AnyIterable[T1], *, key: Callable[[T1], LT] = ..., default: T2
) -> T1 | T2: ...
@overload
async def min(iterable: AnyIterable[LT], *, key: None = ...) -> LT: ...
@overload
async def min(iterable: AnyIterable[LT], *, key: None = ..., default: T) -> LT | T: ...
@overload
async def min(iterable: AnyIterable[T1], *, key: Callable[[T1], LT] = ...) -> T1: ...
@overload
async def min(
    iterable: AnyIterable[T1], *, key: Callable[[T1], LT] = ..., default: T2
) -> T1 | T2: ...
def filter(
    function: Callable[[T], bool] | Callable[[T], Awaitable[bool]] | None,
    iterable: AnyIterable[T],
) -> AsyncIterator[T]: ...
def enumerate(
    iterable: AnyIterable[T], start: int = 0
) -> AsyncIterator[builtins.tuple[int, T]]: ...
@overload
async def sum(iterable: AnyIterable[int]) -> int: ...
@overload
async def sum(iterable: AnyIterable[float]) -> float: ...
@overload
async def sum(iterable: AnyIterable[ADD], start: ADD) -> ADD: ...
async def list(iterable: AnyIterable[T] = ()) -> builtins.list[T]: ...
async def tuple(iterable: AnyIterable[T] = ()) -> builtins.tuple[T, ...]: ...
@overload
async def dict() -> builtins.dict[Any, Any]: ...
@overload
async def dict(
    iterable: AnyIterable[builtins.tuple[HK, T]]
) -> builtins.dict[HK, T]: ...
@overload
async def dict(
    iterable: AnyIterable[builtins.tuple[str, T]] = ..., **kwargs: T
) -> builtins.dict[str, T]: ...
async def set(iterable: AnyIterable[T] = ()) -> builtins.set[T]: ...
@overload
async def sorted(
    iterable: AnyIterable[LT], *, key: None = ..., reverse: bool = ...
) -> builtins.list[LT]: ...
@overload
async def sorted(
    iterable: AnyIterable[T], *, key: Callable[[T], LT], reverse: bool = ...
) -> builtins.list[T]: ...
