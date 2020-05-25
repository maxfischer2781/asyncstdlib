======================
The contextlib library
======================

.. py:module:: asyncstdlib.contextlib
    :synopsis: async contextlib variants

The :py:mod:`asyncstdlib.contextlib` library implements
Python's :py:mod:`contextlib` for (async) iterables and (async) context managers.

Context Managers
================

.. py:class:: AbstractContextManager

    An :term:`abstract base class` for asynchronous context managers

    This class can be used to check whether some object is an
    asynchronous context manager. If a class may inherit from
    ``AbstractContextManager``, in which case it must implement
    an ``__aenter__`` method; the default ``__aenter__`` returns
    the asynchronous context manager itself.

    .. versionadded:: 1.1.0

.. py:function:: contextmanager(func: (...) → async iter T) (...)
    :async-with: :T
    :noindex:

.. autofunction:: contextmanager(func: (...) → async iter T) -> (...) → async with T
    :decorator:

.. autofunction:: closing(thing: AC)
    :async-with: :AC

.. autofunction:: nullcontext(enter_result: T)
    :async-with: :T

.. autoclass:: ExitStack

    .. automethod:: enter_context(cm: (async) with T) -> T

    .. automethod:: callback(callback: T as (*args, **kwargs) -> None, *args, **kwargs) -> T

    .. py:method:: push(exit: T as {.__aexit__}) -> T
        :noindex:

    .. py:method:: push(exit: T as {.__exit__}) -> T
        :noindex:

    .. automethod:: push(exit: T as (Type[BaseException], BaseException, traceback) -> (await) bool) -> T

    .. automethod:: pop_all

    .. automethod:: aclose

    .. versionadded:: 1.1.0