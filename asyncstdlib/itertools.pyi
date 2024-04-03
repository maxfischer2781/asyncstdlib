from typing import (
    Any,
    AsyncIterator,
    AsyncContextManager,
    Awaitable,
    Generic,
    Iterator,
    Iterable,
    Callable,
    TypeVar,
    overload,
)
from typing_extensions import Literal, Self

from ._typing import AnyIterable, ADD, T, T1, T2, T3, T4, T5

def cycle(iterable: AnyIterable[T]) -> AsyncIterator[T]: ...
@overload
def accumulate(iterable: AnyIterable[ADD]) -> AsyncIterator[ADD]: ...
@overload
def accumulate(iterable: AnyIterable[ADD], *, initial: ADD) -> AsyncIterator[ADD]: ...
@overload
def accumulate(
    iterable: AnyIterable[T],
    function: Callable[[T, T], T] | Callable[[T, T], Awaitable[T]],
) -> AsyncIterator[T]: ...
@overload
def accumulate(
    iterable: AnyIterable[T2],
    function: Callable[[T1, T2], T1] | Callable[[T1, T2], Awaitable[T1]],
    *,
    initial: T1,
) -> AsyncIterator[T1]: ...
@overload
def batched(iterable: AnyIterable[T], n: Literal[1]) -> AsyncIterator[tuple[T]]: ...
@overload
def batched(iterable: AnyIterable[T], n: Literal[2]) -> AsyncIterator[tuple[T, T]]: ...
@overload
def batched(
    iterable: AnyIterable[T], n: Literal[3]
) -> AsyncIterator[tuple[T, T, T]]: ...
@overload
def batched(
    iterable: AnyIterable[T], n: Literal[4]
) -> AsyncIterator[tuple[T, T, T, T]]: ...
@overload
def batched(
    iterable: AnyIterable[T], n: Literal[5]
) -> AsyncIterator[tuple[T, T, T, T, T]]: ...
@overload
def batched(
    iterable: AnyIterable[T], n: Literal[6]
) -> AsyncIterator[tuple[T, T, T, T, T, T]]: ...
@overload
def batched(iterable: AnyIterable[T], n: int) -> AsyncIterator[tuple[T, ...]]: ...

class chain(AsyncIterator[T]):
    __slots__: tuple[str, ...]
    def __init__(self, *iterables: AnyIterable[T]) -> None: ...
    @classmethod
    def from_iterable(cls, iterable: AnyIterable[AnyIterable[T]]) -> chain[T]: ...
    async def __anext__(self) -> T: ...
    async def aclose(self) -> None: ...

def compress(data: AnyIterable[T], selectors: AnyIterable[Any]) -> AsyncIterator[T]: ...
def dropwhile(
    predicate: Callable[[T], Any], iterable: AnyIterable[T]
) -> AsyncIterator[T]: ...
def filterfalse(
    predicate: Callable[[T], Any] | None, iterable: AnyIterable[T]
) -> AsyncIterator[T]: ...
@overload
def islice(iterable: AnyIterable[T], start: int | None, /) -> AsyncIterator[T]: ...
@overload
def islice(
    iterable: AnyIterable[T],
    start: int | None,
    stop: int | None,
    step: int | None = None,
    /,
) -> AsyncIterator[T]: ...
@overload
def starmap(
    function: Callable[[T1], T] | Callable[[T1], Awaitable[T]],
    iterable: AnyIterable[tuple[T1]],
) -> AsyncIterator[T]: ...
@overload
def starmap(
    function: Callable[[T1, T2], T] | Callable[[T1, T2], Awaitable[T]],
    iterable: AnyIterable[tuple[T1, T2]],
) -> AsyncIterator[T]: ...
@overload
def starmap(
    function: Callable[[T1, T2, T3], T] | Callable[[T1, T2, T3], Awaitable[T]],
    iterable: AnyIterable[tuple[T1, T2, T3]],
) -> AsyncIterator[T]: ...
@overload
def starmap(
    function: Callable[[T1, T2, T3, T4], T] | Callable[[T1, T2, T3, T4], Awaitable[T]],
    iterable: AnyIterable[tuple[T1, T2, T3, T4]],
) -> AsyncIterator[T]: ...
@overload
def starmap(
    function: (
        Callable[[T1, T2, T3, T4, T5], T] | Callable[[T1, T2, T3, T4, T5], Awaitable[T]]
    ),
    iterable: AnyIterable[tuple[T1, T2, T3, T4, T5]],
) -> AsyncIterator[T]: ...
@overload
def starmap(
    function: Callable[..., T] | Callable[..., Awaitable[T]],
    iterable: AnyIterable[Iterable[Any]],
) -> AsyncIterator[T]: ...
def takewhile(
    predicate: Callable[[T], Any], iterable: AnyIterable[T]
) -> AsyncIterator[T]: ...

class tee(Generic[T]):
    __slots__: tuple[str, ...]

    def __init__(
        self,
        iterable: AnyIterable[T],
        n: int = ...,
        *,
        lock: AsyncContextManager[Any] | None = ...,
    ) -> None: ...
    def __len__(self) -> int: ...
    @overload
    def __getitem__(self, item: int) -> AsyncIterator[T]: ...
    @overload
    def __getitem__(self, item: slice) -> tuple[AsyncIterator[T], ...]: ...
    def __iter__(self) -> Iterator[AnyIterable[T]]: ...
    async def __aenter__(self: Self) -> Self: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool: ...
    async def aclose(self) -> None: ...

def pairwise(iterable: AnyIterable[T]) -> AsyncIterator[tuple[T, T]]: ...

F = TypeVar("F")

@overload
def zip_longest(
    __it1: AnyIterable[T1], *, fillvalue: Any = ...
) -> AsyncIterator[tuple[T1]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
) -> AsyncIterator[tuple[T1 | None, T2 | None]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    *,
    fillvalue: F,
) -> AsyncIterator[tuple[T1 | F, T2 | F]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
) -> AsyncIterator[tuple[T1 | None, T2 | None, T3 | None]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    *,
    fillvalue: F,
) -> AsyncIterator[tuple[T1 | F, T2 | F, T3 | F]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
) -> AsyncIterator[tuple[T1 | None, T2 | None, T3 | None, T4 | None]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    *,
    fillvalue: F,
) -> AsyncIterator[tuple[T1 | F, T2 | F, T3 | F, T4 | F]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    __it5: AnyIterable[T5],
) -> AsyncIterator[tuple[T1 | None, T2 | None, T3 | None, T4 | None, T5 | None]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    __it5: AnyIterable[T5],
    *,
    fillvalue: F,
) -> AsyncIterator[tuple[T1 | F, T2 | F, T3 | F, T4 | F, T5 | F]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T],
    __it2: AnyIterable[T],
    __it3: AnyIterable[T],
    __it4: AnyIterable[T],
    __it5: AnyIterable[T],
    *iterables: AnyIterable[T],
) -> AsyncIterator[tuple[T | None, ...]]: ...
@overload
def zip_longest(
    __it1: AnyIterable[T],
    __it2: AnyIterable[T],
    __it3: AnyIterable[T],
    __it4: AnyIterable[T],
    __it5: AnyIterable[T],
    *iterables: AnyIterable[T],
    fillvalue: F,
) -> AsyncIterator[tuple[T | F, ...]]: ...

K = TypeVar("K")

@overload
def groupby(
    iterable: AnyIterable[T], key: None = ...
) -> AsyncIterator[tuple[T, AsyncIterator[T]]]: ...
@overload
def groupby(
    iterable: AnyIterable[T], key: Callable[[T], Awaitable[K]] | Callable[[T], K]
) -> AsyncIterator[tuple[K, AsyncIterator[T]]]: ...
