from typing import TypeVar
from asyncstdlib import builtins

T = TypeVar("T")


def identity(v: T) -> T:
    return v


async def async_identity(v: T) -> T:
    return v


async def test_min_asyncneutral() -> None:
    await builtins.min([1, 2, 3], key=identity)
    await builtins.min([1, 2, 3], key=async_identity)
