======================
The contextlib library
======================

.. py:module:: asyncstdlib.contextlib
    :synopsis: async contextlib variants

The :py:mod:`asyncstdlib.contextlib` library implements
Python's :py:mod:`contextlib` for (async) iterables and (async) context managers.

Context Managers
================

.. py:function:: contextmanager(func: (...) → async iter T)(...)
    :async-with: :T
    :noindex:

.. autofunction:: contextmanager(func: (...) → async iter T) -> (...) → async with T
    :decorator:

.. autofunction:: closing(thing: AC)
    :async-with: :AC

.. autofunction:: nullcontext(enter_result: T)
    :async-with: :T
