.. _guide_compatible:

================
Sync/Async Reuse
================

The :py:mod:`asyncstdlib` only re-implements functions and classes
that benefit from an async implementation.
In some cases, a synchronous implementation is already
sufficient to cover the async case as well.

Example: async property
=======================

A prominent example is an "``async`` ``property``":
a computed attribute that allows to run ``async`` code as well.
This is useful for example to fetch data for the attribute
from a remote database or server.

As it turns out, we can directly use the builtin :py:class:`property` for this!

.. code-block:: python3

    # python3 -m asyncio
    class Remote:
        _count = 0
        @property                   # <== builtin @property ...
        async def attribute(self):  # ... around an async method
            await asyncio.sleep(1)  # let's pretend to do some work...
            self._count += 1
            return "Na" * self._count

    instance = Remote()
    print(await instance.attribute)  # waits 1 second, prints Na
    print(await instance.attribute)  # waits 1 second, prints NaNa

In principle, we could also define setters and deleters
– however, Python has no syntax for async assignment or deletion
which limits the advantage of using a :py:class:`property` in the first place. [1]_

Identifying reusability
=======================

In general, a utility is sync/async compatible when it takes a callable but does not
depend on the concrete result.
For example, a `property` getter just prepares some attribute value
– which may as well be an awaitable.
In contrast, the similar :py:func:`~asyncstdlib.functools.cached_property` must access
the concrete result to store it – this requires async capabilities for the async case.

Some examples for async compatible parts of the standard library include:

* Factory descriptors such as :py:class:`property`, :py:class:`classmethod` and :py:class:`staticmethod`
* Factories such as :py:func:`functools.partial` and :py:func:`functools.partialmethod`
* Selectors such as :py:func:`functools.singledispatch` and :py:func:`functools.singledispatchmethod`
* Modifiers such as :py:func:`functools.wraps` and :py:func:`functools.update_wrapper`
* Special method operators not enforcing result types such as :py:func:`reversed` and :py:func:`~operator.__add__`

Most of these merely wrap a callable to either modify it directly
(such as :py:func:`functools.wraps`)
or call it regardless of the return type
(such as :py:func:`functools.partial`).
Note that some functions such as :py:func:`~operator.__add__` *usually* work for the
`async` case, but may fail in some subtle edge case – such as not being able to see
a :py:data:`NotImplemented` return value.

.. [1] Using `setattr` and `delattr` one can asynchronously run a setter/getter,
       for example `await setattr(instance, "attribute")`. However, with the lack
       of specific syntax this offers little to no advantage over using a method.
