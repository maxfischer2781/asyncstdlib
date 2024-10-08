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

The test event loop is available via a decorator that should be directly applied
to an ``async def`` test case.

.. autofunction:: sync(test_case: (...) -> (await) None) -> (...) -> None

Async commands
==============

.. autoclass:: Schedule(*await Any)

.. py:class::  Switch(skip: int, /)
    :no-index:

.. py:class::  Switch(min: int, max: int, /)
    :no-index:

.. autoclass:: Switch()

.. autoclass:: Lock
