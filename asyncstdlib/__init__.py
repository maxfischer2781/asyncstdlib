"""itertools in an async world"""
from .builtins import (
    zip,
    map,
    filter,
    enumerate,
    iter,
    all,
    any,
    max,
    min,
    sum,
    list,
    dict,
    set,
    tuple,
)
from .functools import reduce, lru_cache
from .contextlib import closing, contextmanager, nullcontext

__version__ = "0.1.0"

__all__ = [
    "zip",
    "map",
    "filter",
    "enumerate",
    "iter",
    "all",
    "any",
    "max",
    "min",
    "sum",
    "list",
    "dict",
    "set",
    "tuple",
    "reduce",
    "lru_cache",
    "closing",
    "contextmanager",
    "nullcontext",
]
