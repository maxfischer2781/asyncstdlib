======================
The asynctools library
======================

.. py:module:: asyncstdlib.asynctools
    :synopsis: generic asynctools

Iterator lifetime
=================

.. autofunction:: borrow(iterator: async iter T) -> async iter T

.. autofunction:: scoped_iter(iterable: (async) iter T)
    :async-with: :async iter T
