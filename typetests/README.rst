=================
MyPy Type Testing
=================

This suite contains *type* tests for ``asyncstdlib``.
These tests follow similar conventions to unittests but are checked by MyPy.

Test Files
==========

Tests MUST be organised into files, with similar tests grouped together.
Each test file SHOULD be called as per the pattern ``type_<scope>.py``,
where ``<scope>`` describes what the tests cover;
for example, ``test_functools.py`` type-tests the ``functools`` package.

An individual test is a function, method or class and SHOULD be named
with a `test_` or `Test` prefix for functions/methods or classes, respectively.
A class SHOULD be considered a test if it contains any tests.
Tests MUST contain statements to be type-checked:
- plain statements required to be type consistent,
  such as passing parameters of expected correct type to a function.
- assertions about types and exhaustiveness,
  using `typing.assert_type` or `typing.assert_never`.
- statements required to be type inconsistent with an expected type error,
  such as passing parameters of wrong type with `# type: ignore[arg-type]`.

Test files MAY contain non-test functions, methods or classes for use inside tests.
These SHOULD be type-consistent and not require any type assertions or expected errors.

Test Execution
==============

Tests MUST be checked by MyPy using
the ``warn_unused_ignores`` configuration or ``--warn-unused-ignores`` command line
option.
This is required for negative type consistency checks,
i.e. using expected type errors such as ``# type: ignore[arg-type]``.
