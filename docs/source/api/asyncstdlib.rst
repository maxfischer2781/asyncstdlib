==============================
The ``async`` standard library
==============================

.. py:module:: asyncstdlib
    :synopsis: The async standard library

.. toctree::
   :maxdepth: 1
   :hidden:

   builtins

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
