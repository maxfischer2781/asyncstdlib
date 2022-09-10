"""
Helper module to simplify version specific typing imports

This module is for internal use only. Do *not* put any new
"async typing" definitions here.
"""
import sys
from typing import (
    TypeVar,
    Hashable,
    Union,
    AsyncIterable,
    Iterable,
    Callable,
    Any,
    Awaitable,
)

if sys.version_info >= (3, 8):
    from typing import Protocol, AsyncContextManager, ContextManager, TypedDict
else:
    from typing_extensions import (
        Protocol,
        AsyncContextManager,
        ContextManager,
        TypedDict,
    )

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec


__all__ = [
    "Protocol",
    "AsyncContextManager",
    "ContextManager",
    "TypedDict",
    "T",
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "R",
    "AC",
    "HK",
    "LT",
    "ADD",
    "AnyIterable",
    "P",
]

# TypeVars for argument/return type
T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")
T5 = TypeVar("T5")
R = TypeVar("R", covariant=True)
C = TypeVar("C", bound=Callable[..., Any])
AC = TypeVar("AC", bound=Callable[..., Awaitable[Any]])

#: Hashable Key
HK = TypeVar("HK", bound=Hashable)

# LT < LT
LT = TypeVar("LT", bound="SupportsLT")


class SupportsLT(Protocol):
    def __lt__(self: LT, other: LT) -> bool:
        raise NotImplementedError


# ADD + ADD
ADD = TypeVar("ADD", bound="SupportsAdd")


class SupportsAdd(Protocol):
    def __add__(self: ADD, other: ADD) -> ADD:
        raise NotImplementedError


P = ParamSpec("P")


#: (async) iter T
AnyIterable = Union[Iterable[T], AsyncIterable[T]]
