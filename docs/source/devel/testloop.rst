===============
Test Event Loop
===============

.. py:module:: unittests.utility
    :synopsis: testing utilities

To facilitate event loop agnostic features, :py:mod:`asyncstdlib` includes
its own custom event loop implementation for testing.
This is provided as a simple decorator that is compatible with :py:mod:`pytest`,
as well as a number of `async` commands specific to the event loop.

Event Loops
===========

There are currently two event loops available for either simplicity or concurrency.
In case of doubt, prefer :py:func:`~.multi_sync`.

.. autofunction:: sync(test_case: (...) -> (await) None) -> (...) -> None

.. autofunction:: multi_sync(test_case: (...) -> (await) None) -> (...) -> None

Async commands
==============

.. autoclass:: PingPong

.. autoclass:: Schedule(*await Any)

.. autoclass:: Switch

.. autoclass:: Lock
