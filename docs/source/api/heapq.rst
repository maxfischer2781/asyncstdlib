=================
The heapq library
=================

.. py:module:: asyncstdlib.heapq
    :synopsis: async heapq variants

The :py:mod:`asyncstdlib.heapq` library implements
Python's :py:mod:`heapq` for (async) functions and (async) iterables.

.. versionadded:: 3.10.3

This module does not re-implement the functions to maintain a heap data structure.
Since Python's :py:mod:`heapq` module does not support an internal ``key`` function
but relies on ``(key, item)`` pairs as needed,
the same interface can be used for ``async`` key function.
For example, an ``async`` key function would be used as
``heappush(heap, (await key_func(item), item))`` instead of
``heappush(heap, (key_func(item), item))``.

Iterator merging
================

.. autofunction:: merge(*iterables: (async) iter T, key: (T) → (await) Any = None, reverse: bool = False)
    :async-for: :T

Iterator selecting
==================

.. autofunction:: nlargest(*iterables: (async) iter T, n: int, key: (T) → (await) Any = None) -> [T, ...]

.. autofunction:: nsmallest(*iterables: (async) iter T, n: int, key: (T) → (await) Any = None) -> [T, ...]

