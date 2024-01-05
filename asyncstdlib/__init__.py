"""The missing async toolbox"""
from .builtins import (
    anext,
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
    sorted,
)
from .functools import reduce, lru_cache, cache, cached_property
from .contextlib import closing, contextmanager, nullcontext, ExitStack
from .itertools import (
    accumulate,
    batched,
    cycle,
    chain,
    compress,
    dropwhile,
    filterfalse,
    islice,
    takewhile,
    starmap,
    tee,
    pairwise,
    zip_longest,
    groupby,
)
from .asynctools import borrow, scoped_iter, await_each, any_iter, apply, sync
from .heapq import merge, nlargest, nsmallest

__version__ = "3.12.0"

__all__ = [
    "anext",
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
    "sorted",
    # functools
    "reduce",
    "lru_cache",
    "cache",
    "cached_property",
    # contextlib
    "closing",
    "contextmanager",
    "nullcontext",
    "ExitStack",
    # itertools
    "accumulate",
    "batched",
    "cycle",
    "chain",
    "compress",
    "dropwhile",
    "filterfalse",
    "takewhile",
    "islice",
    "starmap",
    "tee",
    "pairwise",
    "zip_longest",
    "groupby",
    # asynctools
    "borrow",
    "scoped_iter",
    "await_each",
    "any_iter",
    "apply",
    "sync",
    # heapq
    "merge",
    "nlargest",
    "nsmallest",
]
