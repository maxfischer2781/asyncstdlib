=======================
Contribution Guidelines
=======================

Contributions to ``asyncstdlib`` are highly welcome!
The place to go is the `asyncstdlib GitHub repository`_
where you can report bugs, request improvements or propose changes.

- For bug reports and feature requests simply `open a new issue`_
  and fill in the appropriate template.
- Even for content submissions it is highly recommended to make sure an issue
  exists - this allows you to get early feedback and document the development.
  You can use whatever tooling you like to create the content,
  but the next sections give a rough outline on how to proceed.

.. _asyncstdlib GitHub repository: https://github.com/maxfischer2781/asyncstdlib
.. _open a new issue: https://github.com/maxfischer2781/asyncstdlib/issues/new/choose

Submitting Content
==================

To submit concrete content suggestions you *must* use a `GitHub Fork and Pull Request`_.
This lets you create the content at your own pace yet still receive direct feedback.
Feel free to start with a *Draft Pull Request* to get feedback early.

All content goes through mandatory automated and manual review.
You can run most of the automated review yourself to get faster feedback,
yet it is also fine to wait for the checks run on GitHub itself.
Dependencies for automated code and documentation checking is available via
the extras ``test`` and ``doc``, respectively.

.. note::

    Ideally you develop with the repository checked out locally and a separate `Python venv`_.
    If you have the venv active and the current working directory is the repository root,
    simply run `python -m pip install -e '.[test,doc]'` to install all dependencies.

.. _`GitHub Fork and Pull Request`: https://guides.github.com/activities/forking/
.. _`Python venv`: https://docs.python.org/3/library/venv.html

Testing Code
------------

Code is verified locally using the tools `flake8`, `black`, `pytest` and `mypy`.
If you do not have your own preferences we recommend the following order:

.. code:: bash

    python -m black asyncstdlib unittests
    python -m flake8 asyncstdlib unittests
    python -m pytest
    python -m mypy --pretty

This runs tests from simplest to most advanced and should allow you quick development.
Note that some additional checks are run on GitHub to check test coverage and code health.

Building Docs
-------------

If you change the documentation, either directly or via significant edits to docstrings,
you can build the documentation yourself to check if everything renders as expected.
To do so, trigger a `Sphinx build`_ to generate a HTML version of the docs:

.. code:: bash

    sphinx-build -M html ./docs ./docs/_build

On success, simply open `./docs/_build/html/index.html` in your favourite browser.

.. _`Sphinx build`: https://www.sphinx-doc.org/en/master/man/sphinx-build.html

The Review
----------

Once you mark your pull request as ready for review, be prepared for one or more rounds of comments.
These can range from general commentary, to code suggestions, to inquiries why a specific change was made.
We strive to give actionable advice, but whenever you have trouble understanding how to proceed -
please just reply with a comment of your own and ask how to proceed!

Once all comments are resolved and your pull request was approved, sit back and relax!
We will merge your pull request in due time and include it in the next release.
Thanks for contributing!
