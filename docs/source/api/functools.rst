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

Async Caches
============

The regular :py:func:`functools.lru_cache` and :py:func:`functools.cached_property`
are not appropriate for
async callables, such as an ``async def`` :term:`coroutine function`:
their direct return value is an :term:`awaitable` instead of the desired value.
This causes the cache to store only temporary helpers, not the actual values.

Both :py:func:`~asyncstdlib.functools.lru_cache`
and :py:func:`~asyncstdlib.functools.cached_property`
of :py:mod:`asyncstdlib` work only with async callables
(they are not :term:`async neutral`).
Notably, this includes regular callables that return an :term:`awaitable`,
such as an ``async def`` function wrapped by :py:func:`~functools.partial`.

.. autofunction:: cached_property(getter: (Self) → await T)
    :decorator:

    .. versionadded:: 1.1.0

The :py:func:`~asyncstdlib.functools.lru_cache`
can be applied as a decorator, both with and without arguments:

.. code-block:: python3

    @a.lru_cache
    async def get_pep(num):
        url = f'http://www.python.org/dev/peps/pep-{num:04}/'
        request = await asynclib.get(url)
        return request.body()

    @a.lru_cache(maxsize=32)
    async def get_pep(num):
        url = f'http://www.python.org/dev/peps/pep-{num:04}/'
        request = await asynclib.get(url)
        return request.body()

.. autofunction:: cache((...) -> await R)
    :decorator:

    .. versionadded:: 3.9.0

.. autofunction:: lru_cache(maxsize: ?int = 128, typed: bool = False)((...) -> await R)
    :decorator:

The cache tracks *call argument patterns* and maps them to observed return values.
A pattern is an *ordered* representation of provided positional and keyword arguments;
notably, this disregards default arguments, as well as any overlap between
positional and keyword arguments.
This means that for a function ``f(a, b)``, the calls ``f(1, 2)``, ``f(a=1, b=2)``
and ``f(b=2, a=1)`` are considered three distinct patterns.

In addition, exceptions are not return values. This allows retrying a long-running
query that may fail, caching any *eventual* result for quick and reliable lookup.

A wrapped async callable can be queried for its cache metadata,
and allows clearing the entire cache. This can be useful to explicitly monitor
cache performance, and to manage caches of unrestricted size.
Note that the ``maxsize`` of a cache cannot be changed at runtime -- however,
the ``__wrapped__`` callable may be wrapped with a new cache of different size.

.. autoclass:: LRUAsyncCallable()

    .. py:attribute:: __wrapped__

        The callable wrapped by this cache

    .. automethod:: __call__(...) -> await R

    .. automethod:: cache_clear()

    .. automethod:: cache_info() -> (hits=..., misses=..., maxsize=..., currsize=...)

    .. automethod:: cache_parameters() -> {"maxsize": ..., "typed": ...}

    .. versionadded:: 3.9.0

        The :py:meth:`~.cache_parameters` method.
