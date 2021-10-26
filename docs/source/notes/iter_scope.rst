.. _guide_iteration:

================
Iterator Scoping
================

Cleanup of ``async`` resources is special in that it may require an active event loop.
Since :term:`asynchronous iterators <python:asynchronous iterator>` can hold resources
indefinitely, they should be cleaned up deterministically whenever possible
(see `PEP 533`_ for discussion).
Thus, ``asyncstdlib`` defaults to deterministic cleanup but provides tools to explicitly
manage the lifetime of iterators.

Cleanup in ``asyncstdlib``
==========================

All async iterators of :py:mod:`asyncstdlib` that work on other iterators
assume sole ownership of the iterators passed to them.
Passed in async iterators are guaranteed to be :py:meth:`~agen.aclose`\ d
as soon as the :py:mod:`asyncstdlib` async iterator itself is cleaned up.
This provides a resource-safe default for the most common operation of
exhausting iterators.

.. code-block:: python3

    >>> import asyncio
    >>> import asyncstdlib as a
    >>>
    >>> async def async_squares(i=0):
    ...     """Provide an infinite stream of squared numbers"""
    ...     while True:
    ...         await asyncio.sleep(0.1)
    ...         yield i**2
    ...         i += 1
    ...
    >>> async def main():
    ...     async_iter = async_squares()
    ...     # loop until we are done
    ...     async for i, s in a.zip(range(5), async_iter):
    ...         print(f"{i}: {s}")
    ...     assert await a.anext(async_iter, "Closed!") == "Closed!"
    ...
    >>> asyncio.run(main())

For consistency, every :py:mod:`asyncstdlib` async iterator performs such cleanup.
This may be unexpected for async variants of iterator utilities that are usually
applied multiple times, such as :py:func:`itertools.islice`.
Thus, to manage the lifetime of async iterators one can explicitly scope them.

Scoping async iterator lifetime
===============================

In order to use a single async iterator across several iterations but guarantee cleanup,
the iterator can be scoped to an ``async with`` block:
using :py:func:`asyncstdlib.scoped_iter` creates an async iterator that is guaranteed
to :py:meth:`~agen.aclose` at the end of the block, but cannot be closed before.

.. code-block:: python3

    >>> import asyncio
    >>> import asyncstdlib as a
    >>>
    >>> async def async_squares(i=0):
    ...     """Provide an infinite stream of squared numbers"""
    ...     while True:
    ...         await asyncio.sleep(0.1)
    ...         yield i**2
    ...         i += 1
    ...
    >>> async def main():
    ...     # iterator can be re-used in the async with block
    ...     async with a.scoped_iter(async_squares()) as async_iter:
    ...         async for s in a.islice(async_iter, 3):
    ...             print(f"1st Batch: {s}")
    ...         # async_iter is still open for further iteration
    ...         async for s in a.islice(async_iter, 3):
    ...             print(f"2nd Batch: {s}")
    ...         async for s in a.islice(async_iter, 3):
    ...             print(f"3rd Batch: {s}")
    ...     # iterator is closed after the async with block
    ...     assert await a.anext(async_iter, "Closed!") == "Closed!"
    ...
    >>> asyncio.run(main())

Scoped iterators should be the go-to approach for managing iterator lifetimes.
However, not all lifetimes correspond to well-defined lexical scopes;
for these cases, one can :term:`borrow <borrowing>` an iterator instead.

.. _PEP 533: https://www.python.org/dev/peps/pep-0533/
