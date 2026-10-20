from typing import TypeVar, Optional, Union, List, Dict
from typing_extensions import assert_type
from asyncstdlib import builtins

T = TypeVar("T")


def identity(v: T) -> T:
    return v


async def async_identity(v: T) -> T:
    return v


async def test_min_asyncneutral() -> None:
    await builtins.min([1, 2, 3], key=identity)
    await builtins.min([1, 2, 3], key=async_identity)


async def test_extrema_independent_default_type() -> None:
    records: List[Dict[str, int]] = [{"priority": 1}]

    def priority(record: Dict[str, int]) -> int:
        return record["priority"]

    async def async_priority(record: Dict[str, int]) -> int:
        return record["priority"]

    assert_type(await builtins.min(records, key=priority), Dict[str, int])
    assert_type(await builtins.max(records, key=async_priority), Dict[str, int])
    assert_type(
        await builtins.min(records, key=priority, default=None),
        Optional[Dict[str, int]],
    )
    assert_type(
        await builtins.max(records, key=async_priority, default=None),
        Optional[Dict[str, int]],
    )
    assert_type(await builtins.min([1], default="empty"), Union[int, str])
    assert_type(await builtins.max([1], default="empty"), Union[int, str])
