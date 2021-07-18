.. asyncstdlib documentation master file, created by
   sphinx-quickstart on Tue Mar 26 15:06:09 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=============================
The missing ``async`` toolbox
=============================

.. image:: https://readthedocs.org/projects/asyncstdlib/badge/?version=latest
    :target: http://asyncstdlib.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/asyncstdlib.svg
    :alt: Available on PyPI
    :target: https://pypi.python.org/pypi/asyncstdlib/

.. image:: https://anaconda.org/conda-forge/asyncstdlib/badges/version.svg
    :alt: Available on Conda-Forge
    :target: https://anaconda.org/conda-forge/asyncstdlib

.. image:: https://img.shields.io/github/license/maxfischer2781/asyncstdlib.svg
    :alt: License
    :target: https://github.com/maxfischer2781/asyncstdlib/blob/master/LICENSE

.. image:: https://badges.gitter.im/maxfischer2781/asyncstdlib.svg
    :target: https://gitter.im/maxfischer2781/asyncstdlib?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
    :alt: Development Chat

.. py:module:: asyncstdlib
    :synopsis: The async standard library

.. toctree::
   :maxdepth: 1
   :caption: The Async Toolbox
   :hidden:

   source/api/builtins
   source/api/functools
   source/api/contextlib
   source/api/itertools
   source/api/asynctools
   source/glossary

.. toctree::
   :maxdepth: 1
   :caption: Development & Maintenance
   :hidden:

   source/contributing
   source/publishing

The ``asyncstdlib`` library re-implements functions and classes of the Python
standard library to make them compatible with ``async`` callables, iterables
and context managers.
It is fully agnostic to ``async`` event loops and seamlessly works with
:py:mod:`asyncio`, third-party libraries such as :py:mod:`trio`, as well as
any custom ``async`` event loop.

Standard Library Modules
========================

All re-implementations are located in submodules of :py:mod:`asyncstdlib`
with the same name as those of the Python standard library.

:py:mod:`asyncstdlib.builtins`
    Replicates any :ref:`built-in-funcs` that benefit from being asynchronous,
    such as :py:func:`~asyncstdlib.builtins.zip`,
    :py:func:`~asyncstdlib.builtins.sum`,
    or :py:func:`~asyncstdlib.builtins.list`.

:py:mod:`asyncstdlib.functools`
    Replicates any :py:mod:`functools` that benefit from being asynchronous,
    which is just :py:func:`~asyncstdlib.functools.reduce`,
    :py:func:`~asyncstdlib.functools.cached_property`, and
    :py:func:`~asyncstdlib.functools.lru_cache`.

:py:mod:`asyncstdlib.contextlib`
    Replicates any :py:mod:`contextlib` tools that benefit from being asynchronous,
    such as :py:func:`~asyncstdlib.contextlib.contextmanager`, or
    :py:func:`~asyncstdlib.contextlib.closing`.

:py:mod:`asyncstdlib.itertools`
    Replicates any :py:mod:`itertools` that benefit from being asynchronous,
    such as :py:func:`~asyncstdlib.itertools.cycle`,
    :py:func:`~asyncstdlib.itertools.chain`,
    or :py:func:`~asyncstdlib.itertools.accumulate`.

For simplicity, the :py:mod:`asyncstdlib` namespace also exposes all individual
functions and classes directly.
For example, :py:mod:`asyncstdlib.builtins.enumerate` is also available
as ``asyncstdlib.enumerate``.

The Async Library Module
========================

The core toolset used by :py:mod:`asyncstdlib` itself is available
as a separate submodule.

:py:mod:`asyncstdlib.asynctools`
    Collects any :py:mod:`asyncstdlib` tools useful for building
    well-behaved ``async`` helpers and programs.

Async Neutral Arguments
=======================

Many objects of :py:mod:`asyncstdlib` are :term:`async neutral` -- they accept
*both* regular and async arguments.
Type annotations use *(async)* to denote async neutral objects.
For example, the annotation *(int, ...) → (async) bool* denotes a call that takes an
:py:class:`int` and either returns a boolean directly *or* requires ``await`` to
return a boolean.

Whether a call is regular or async is determined by inspecting its
return type at runtime.
This supports async-producing factories, such as an ``async def``
function wrapped in :py:class:`functools.partial`.
However, this also means that the result must consistently be *either*
regular or async.

Note that only *arguments* to :py:mod:`asyncstdlib` may be async neutral.
All callables of :py:mod:`asyncstdlib` consistently provide
:term:`awaitables <awaitable>`,
:term:`asynchronous iterators <asynchronous iterator>`, and
:term:`asynchronous context managers <asynchronous context manager>`.

Async Iterator Cleanup
======================

Cleanup of async iterables is special in that :py:meth:`~agen.aclose` may require
an active event loop. This is not given when garbage collection finalizes an
async iterable via its :py:meth:`~object.__del__` method. Thus, async iterators
should be cleaned up deterministically whenever possible (see `PEP 533`_ for details).

All async iterators of :py:mod:`asyncstdlib` that work on other iterators
assume sole ownership of the iterators passed to them.
Passed in async iterators are guaranteed to :py:meth:`~agen.aclose` as soon as
the :py:mod:`asyncstdlib` async iterator itself is cleaned up.
Use :py:func:`~asyncstdlib.asynctools.borrow` to prevent automatic cleanup,
and :py:func:`~asyncstdlib.asynctools.scoped_iter` to guarantee cleanup in custom code.

.. _PEP 533: https://www.python.org/dev/peps/pep-0533/

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

