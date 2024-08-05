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
Notably, they also work with regular callables that return an :term:`awaitable`,
such as an ``async def`` function wrapped by :py:func:`~functools.partial`.

Attribute Caches
----------------

This type of cache tracks ``await``\ ing an attribute.

.. py:function:: cached_property(getter: (Self) → await T, /) -> await T
    :decorator:

.. autofunction:: cached_property(context_type: Type[AsyncContextManager], /)((Self) → await T) -> await T
    :decorator:
    :noindex:

    .. versionadded:: 1.1.0
    .. versionadded:: 3.12.5

        The ``context_type`` decorator parameter.


Callable Caches
---------------

This type of cache tracks *call argument patterns* and their return values.
A pattern is an *ordered* representation of positional and keyword arguments;
notably, this disregards defaults and overlap between positional and keyword arguments.
This means that for a function ``f(a, b)``, the calls ``f(1, 2)``, ``f(a=1, b=2)``
and ``f(b=2, a=1)`` are considered three distinct patterns.

Note that exceptions are not considered return values and thus never cached. This makes
the caches suitable for queries that may fail, caching any *eventual* result for
quick and reliable lookup.

.. autofunction:: cache((...) → await R) -> LRUAsyncCallable
    :decorator:

    .. versionadded:: 3.9.0

.. py:function:: lru_cache((...) → await R) -> LRUAsyncCallable
    :decorator:
    :noindex:

.. autofunction:: lru_cache(maxsize: ?int = 128, typed: bool = False)((...) → await R) -> LRUAsyncCallable
    :decorator:

A cached async callable can be queried for its cache metadata and allows clearing
entries from the cache. This can be useful to explicitly monitor cache performance,
and to manage caches of unrestricted size.
While the ``maxsize`` of a cache cannot be changed at runtime,
the ``__wrapped__`` callable may be wrapped with a new cache of different size.

.. autoclass:: LRUAsyncCallable()

    .. py:attribute:: __wrapped__

        The callable wrapped by this cache

    .. automethod:: __call__(...) -> await R

    .. automethod:: cache_clear()

    .. automethod:: cache_discard(...)

        .. versionchanged:: Python3.9
            :py:func:`classmethod` properly wraps caches.

        .. versionchanged:: Python3.13
            :py:func:`classmethod` no longer wraps caches in a way that supports `cache_discard`.

        .. versionadded:: 3.10.4

    .. automethod:: cache_info() -> (hits=..., misses=..., maxsize=..., currsize=...)

    .. automethod:: cache_parameters() -> {"maxsize": ..., "typed": ...}

        .. versionadded:: 3.9.0
