=====================
The functools library
=====================

.. py:module:: asyncstdlib.functools
    :synopsis: async functools variants

The :py:mod:`asyncstdlib.functools` library implements
Python's :py:mod:`functools` for (async) functions and (async) iterables.

Iterator reducing
=================

.. autofunction:: reduce(function: (T, T) → (await) T, iterable: (async) iter T, initial: T) -> T
    :async:

Async Function Cache
====================

.. autofunction:: lru_cache
    :decorator:

The cache tracks *call argument patterns* and maps them to observed return values.
A pattern is an *ordered* representation of positional and keyword arguments;
notably, this disregards default arguments, as well as any overlap between
positional and keyword arguments.
This means that for a function ``f(a, b)``, the calls ``f(1, 2)``, ``f(a=1, b=2)``
and ``f(b=2, a=1)`` are considered three distinct patterns.

In addition, exceptions are not return values. This allows retrying a long-running
query that may fail, caching any *eventual* result for quick and reliable lookup.

.. autoclass:: LRUAsyncCallable

    .. py:attribute:: __wrapped__

        The callable wrapped by this cache

    .. automethod:: __call__(...) -> R

    .. automethod:: cache_clear()

    .. automethod:: cache_info() -> CacheInfo


.. autoclass:: CacheInfo

    .. py:attribute:: hits

        Number of hits so far, i.e. results read from the cache

    .. py:attribute:: misses

        Number of misses, i.e. freshly computed results

    .. py:attribute:: maxsize

        The maximum number of cache entries or :py:data:`None` for an unbounded cache

    .. py:attribute:: currsize

        The current number of cache entries