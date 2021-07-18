================================================
``asyncstdlib`` -- the missing ``async`` toolbox
================================================

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

The ``asyncstdlib`` library re-implements functions and classes of the Python
standard library to make them compatible with ``async`` callables, iterables
and context managers.
It is fully agnostic to ``async`` event loops and seamlessly works with
``asyncio``, third-party libraries such as ``trio``, as well as
any custom ``async`` event loop.

* Full set of ``async`` versions of advantageous standard library helpers,
  such as ``zip``, ``map``, ``enumerate``, ``functools.reduce``,
  ``itertools.tee``, ``itertools.groupby`` and many others.
* Safe handling of ``async`` iterators to ensure prompt cleanup, as well as
  various helpers to simplify safely using custom ``async`` iterators.
* Small but powerful toolset to seamlessly integrate existing sync code
  into ``async`` programs and libraries.

Check out the `documentation`_ to get started or take a look around.

.. _documentation: http://asyncstdlib.readthedocs.io/