====================
The builtins library
====================

.. py:module:: asyncstdlib.builtins
    :synopsis: async builtins variants

The :py:mod:`asyncstdlib.builtins` library implements
Python's :ref:`built-in-funcs` for (async) functions and (async) iterables.

Iterator reducing
=================

.. autofunction:: anext(iterable: async iter T [, default: T]) -> T
    :async:

.. autofunction:: all(iterable: (async) iter T) -> bool
    :async:

.. autofunction:: any(iterable: (async) iter T) -> bool
    :async:

.. autofunction:: max(iterable: (async) iter T, *, key: (T) → Any, default: T) -> T
    :async:

.. autofunction:: min(iterable: (async) iter T, *, key: (T) → Any, default: T) -> T
    :async:

.. autofunction:: sum(iterable: (async) iter T, start: T = 0) -> T
    :async:

Iterator transforming
=====================

.. autofunction:: iter(iterable: (async) iter T)
    :async-for: :T

.. autofunction:: filter(function: (T) → (await) bool, iterable: (async) iter T)
    :async-for: :T

.. autofunction:: zip(*iterables: (async) iter T, strict: bool = True)
    :async-for: :(T, ...)

    .. versionadded:: 3.10.0

        The ``strict`` parameter.

.. autofunction:: map(function: (T, ...) → (await) R, iterable: (async) iter T, ...)
    :async-for: :R

.. autofunction:: enumerate(iterable: (async) iter T, start=0)
    :async-for: :(int, T)

Standard types
==============

.. autofunction:: dict(iterable: (async) iter (str, T) = ()) -> {str: T, ...}
    :async:

.. autofunction:: list(iterable: (async) iter T = ()) -> [T, ...]
    :async:

.. autofunction:: set(iterable: (async) iter T = ()) -> {T, ...}
    :async:

.. autofunction:: tuple(iterable: (async) iter T = ()) -> (T, ...)
    :async:

.. autofunction:: sorted(iterable: (async) iter T, *, key: (T) → (await) Any, reverse: bool) -> [T, ...]
    :async:

    .. versionadded:: 3.9.0
