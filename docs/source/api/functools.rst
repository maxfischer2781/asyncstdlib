=====================
The functools library
=====================

.. py:module:: asyncstdlib.functools
    :synopsis: async functools variants

The :py:mod:`asyncstdlib.functools` library implements
Python's :py:mod:`functools` for (async) functions and (async) iterables.

.. autofunction:: reduce(function: (T, T) → (await) T, iterable: (async) iter T, initial: T) -> T
    :async:
