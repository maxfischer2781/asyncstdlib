from typing import TypeVar, assert_type
from asyncstdlib import builtins

T = TypeVar("T")


def identity(v: T) -> T:
    return v


async def async_identity(v: T) -> T:
    return v


async def test_min_asyncneutral() -> None:
    await builtins.min([1, 2, 3], key=identity)
    await builtins.min([1, 2, 3], key=async_identity)


async def test_max_asyncneutral() -> None:
    await builtins.max([1, 2, 3], key=identity)
    await builtins.max([1, 2, 3], key=async_identity)


async def test_minmax_default() -> None:
    assert_type(await builtins.min([1, 2], default="str"), int | str)
    assert_type(await builtins.max([1, 2], default="str"), int | str)
