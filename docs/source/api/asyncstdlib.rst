==============================
The ``async`` standard library
==============================

.. py:module:: asyncstdlib
    :synopsis: The async standard library

.. toctree::
   :maxdepth: 1
   :hidden:

   builtins
   functools
   contextlib
   itertools

The ``asyncstdlib`` library re-implements functions and classes of the Python
standard library to make them compatible with ``async`` callables, iterables
and context managers.
Unless otherwise noted, all objects are :term:`async neutral` -- they accept
*both* regular and async arguments.

Type annotations use *(async)* to denote async neutral objects.
For example, the annotation *(int, ...) → (async) bool* denotes a call that
returns a boolean directly *or* requires ``await`` to return a boolean.

.. note::

    Whether a call is regular or async is determined by inspecting its
    return type at runtime.
    This supports async-producing factories, such as an ``async def``
    function wrapped in :py:class:`functools.partial`.
    However, this also means that the result must consistently be *either*
    regular or async.

All re-implementations are located in submodules of :py:mod:`asyncstdlib`
with the same name as those of the Python standard library.
For simplicity, the :py:mod:`asyncstdlib` namespace also exposes all individual
functions and classes directly.
For example, :py:mod:`asyncstdlib.builtins.enumerate` is also available
as ``asyncstdlib.enumerate``.

Async Neutral Modules
=====================

:py:mod:`asyncstdlib.builtins`
    Replicates any :ref:`built-in-funcs` that take an :term:`iterable`,
    such as :py:func:`~asyncstdlib.builtins.zip`, :py:func:`~asyncstdlib.builtins.sum`
    or :py:func:`~asyncstdlib.builtins.list`.

:py:mod:`asyncstdlib.functools`
    Replicates any :py:mod:`functools` that take an :term:`iterable`,
    which is just :py:func:`~asyncstdlib.functools.reduce`
    and :py:func:`~asyncstdlib.functools.lru_cache`.

:py:mod:`asyncstdlib.contextlib`
    Replicates any :py:mod:`contextlib` objects working with an :term:`iterable`
    or :term:`context manager`,
    such as :py:func:`~asyncstdlib.contextlib.contextmanager` or
    :py:func:`~asyncstdlib.contextlib.closing`.

:py:mod:`asyncstdlib.itertools`
    Replicates any :py:mod:`itertools` that lazily take an :term:`iterable`,
    such as :py:func:`~asyncstdlib.itertools.cycle`,
    :py:func:`~asyncstdlib.itertools.chain`
    or :py:func:`~asyncstdlib.itertools.accumulate`.

Async Iterable Cleanup
======================

Cleanup of async iterables is special in that :py:meth:`~agen.aclose` may require
an active event loop. This is not given when garbage collection finalizes an
async iterable via its :py:meth:`~object.__del__` method. Thus, async iterators
should be cleaned up deterministically whenever possible (see `PEP 533`_ for details).

Whenever an async iterator of :py:mod:`asyncstdlib` creates a temporary
async iterator [#tempiter]_ during iteration, it assumes sole ownership of this iterator.
It guarantees to clean up such temporary async iterators as soon as
the :py:mod:`asyncstdlib` async iterator itself is cleaned up.

.. [#tempiter] An iterator ``aiter = a.iter(source)`` is assumed to be temporary if
         it is a new object, that is ``aiter is not source`` holds true.

.. _PEP 533: https://www.python.org/dev/peps/pep-0533/
