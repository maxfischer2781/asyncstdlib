=====================
The itertools library
=====================

.. py:module:: asyncstdlib.itertools
    :synopsis: async itertools variants

The :py:mod:`asyncstdlib.itertools` library implements
Python's :py:mod:`itertools` for (async) functions and (async) iterables.

.. note::

    Only functions which benefit from an explicit ``async`` implementation are provided.
    Other functions from ``itertools`` can be turned asynchronous using :py:func:`~asyncstdlib.iter`,
    e.g. `asyncstdlib.iter(itertools.count(5))`.

.. note::

    To avoid leaking resources, all utilities in this module explicitly close their
    iterable arguments when done.
    This can be unexpected for non-exhausting utilities such as :py:func:`~.dropwhile`
    and may require explicit scoping.
    See the guide on :ref:`guide_iteration` for details and usage examples.

Infinite iterators
==================

.. autofunction:: cycle(iterable: (async) iter T)
    :async-for: :T

Iterator merging
================

.. autofunction:: chain(*iterables: (async) iter T)
    :async-for: :T

.. autofunction:: asyncstdlib.itertools::chain.from_iterable(iterable: (async) iter (async) iter T)
    :async-for: :T

.. autofunction:: zip_longest(*iterables: (async) iter T, fillvalue: S = None)
    :async-for: :(T or S, ...)

Iterator filtering
==================

.. autofunction:: compress(data: (async) iter T, selectors: (async) iter T)
    :async-for: :T

.. autofunction:: dropwhile(predicate: (T) → (await) bool, iterable: (async) iter T)
    :async-for: :T

.. autofunction:: filterfalse(predicate: None | (T) → (await) bool, iterable: (async) iter T)
    :async-for: :T

.. autofunction:: takewhile(predicate: (T) → (await) bool, iterable: (async) iter T)
    :async-for: :T

.. py:function:: islice(iterable: (async) iter T, stop: int)
    :async-for: :T
    :noindex:

.. autofunction:: islice(iterable: (async) iter T, start: int, stop: int , step: int =m1)
    :async-for: :T

Iterator transforming
=====================

.. autofunction:: accumulate(iterable: (async) iter T, function: (T, T) → (await) T = add [, initial: T])
    :async-for: :T

    .. versionchanged:: 3.13.2

        ``initial=None`` means no initial value is assumed.

.. autofunction:: starmap(function: (*A) → (await) T, iterable: (async) iter (A, ...))
    :async-for: :T

Iterator splitting
==================

.. autofunction:: tee(iterable: (async) iter T, n: int = 2, [*, lock: async with Any])
    :for: :(async iter T, ...)

    .. versionadded:: 3.10.5

        The ``lock`` keyword parameter.

    .. versionchanged:: 3.13.2

        ``tee``\ s share their buffer with parents, siblings and children.

.. autofunction:: pairwise(iterable: (async) iter T)
    :async-for: :(T, T)

    .. versionadded:: 3.10.0

.. autofunction:: batched(iterable: (async) iter T, n: int, strict: bool = False)
    :async-for: :T

    .. versionadded:: 3.11.0

    .. versionadded:: 3.13.0

        The ``strict`` parameter.

.. py:function:: groupby(iterable: (async) iter T)
    :async-for: :(T, async iter T)
    :noindex:
.. autofunction:: groupby(iterable: (async) iter T, key: (T) → (await) R)
    :async-for: :(R, async iter T)

    .. versionadded:: 1.1.0
