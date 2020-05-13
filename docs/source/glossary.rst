=================
Glossary of Terms
=================

.. Using references in the glossary itself:
   When mentioning other items, always reference them.
   When mentioning the current item, never reference it.


.. glossary::

   async neutral
      An object that may provide either of a regular or asynchronous implementation.
      For example, an async neutral iterable may support either regular
      ``for _ in iterable`` or asynchronous ``async for _ in iterable`` iteration.

   borrowing
   borrowed object
      Many ``async`` object need to be cleaned up explicitly – for example,
      an :term:`asynchronous iterator` should generally be ``aclose``d after use
      (see `PEP 533`_ for details). When *borrowing* such an object, the original
      owner assures that it will clean up the object. As such, a *borrowed object*
      can only be cleaned up by the original owner.

.. _PEP 533: https://www.python.org/dev/peps/pep-0533/