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
from .itertools import (
    accumulate,
    cycle,
    chain,
    compress,
    dropwhile,
    islice,
    takewhile,
    starmap,
)

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
    # functools
    "reduce",
    "lru_cache",
    # contextlib
    "closing",
    "contextmanager",
    "nullcontext",
    # itertools
    "accumulate",
    "cycle",
    "chain",
    "compress",
    "dropwhile",
    "takewhile",
    "islice",
    "starmap",
]
