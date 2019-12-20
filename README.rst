================================================
``asyncstdlib`` -- the missing ``async`` toolbox
================================================

.. image:: https://readthedocs.org/projects/asyncstdlib/badge/?version=latest
    :target: http://asyncstdlib.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/asyncstdlib.svg
    :alt: Available on PyPI
    :target: https://pypi.python.org/pypi/asyncstdlib/

.. image:: https://img.shields.io/github/license/maxfischer2781/asyncstdlib.svg
    :alt: License
    :target: https://github.com/maxfischer2781/asyncstdlib/blob/master/LICENSE

The ``asyncstdlib`` library re-implements functions and classes of the Python
standard library to make them compatible with ``async`` callables, iterables
and context managers.
It is fully agnostic to ``async`` event loops and seamlessly works with
``asyncio``, third-party libraries such as ``trio``, as well as
any custom ``async`` event loop.
