from typing import (
    TypeVar,
    Generic,
    AsyncGenerator,
    Callable,
    Optional,
    Union,
    Any,
    Awaitable,
    Deque,
    overload,
)
from functools import wraps
from collections import deque
from functools import partial
import sys

from ._typing import Protocol, AsyncContextManager, ContextManager, T, C
from ._core import awaitify
from ._utility import public_module, slot_get as _slot_get


AnyContextManager = Union[AsyncContextManager[T], ContextManager[T]]


# typing.AsyncContextManager uses contextlib.AbstractAsyncContextManager if available,
# and a custom implementation otherwise. No need to replicate it.
AbstractContextManager = AsyncContextManager


class ACloseable(Protocol):
    async def aclose(self) -> None:
        """Asynchronously close this object"""


AC = TypeVar("AC", bound=ACloseable)


def contextmanager(
    func: Callable[..., AsyncGenerator[T, None]]
) -> Callable[..., AsyncContextManager[T]]:
    """
    Create an asynchronous context manager out of an asynchronous generator function

    This is intended as a decorator for an asynchronous generator function.
    The asynchronous generator should ``yield`` once, at which point the body of the
    context manager executes. If ``yield`` provides a value, this becomes the value
    of the context in the block.

    .. code-block:: python3

        @contextmanager
        async def Context(*args, **kwargs):
            # __aenter__
            yield  # context value
            # __aexit__

    Note that if an exception ends the context block, it gets re-raised at the ``yield``
    inside the asynchronous generator (via :py:meth:`~agen.athrow`). In order to handle
    this exception, the ``yield`` should be wrapped in a ``try`` statement.
    """

    @wraps(func)
    def helper(*args: Any, **kwds: Any) -> AsyncContextManager[T]:
        return _AsyncGeneratorContextManager(func, args, kwds)

    return helper


class _AsyncGeneratorContextManager(Generic[T]):
    def __init__(
        self, func: Callable[..., AsyncGenerator[T, None]], args: Any, kwds: Any
    ):
        self.gen = func(*args, **kwds)
        self.__doc__ = getattr(func, "__doc__", type(self).__doc__)

    async def __aenter__(self) -> T:
        try:
            return await self.gen.__anext__()
        except StopAsyncIteration:
            raise RuntimeError("generator did not yield to __aenter__") from None

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is None:
            try:
                await self.gen.__anext__()
            except StopAsyncIteration:
                return False
            else:
                raise RuntimeError("generator did not stop after __aexit__")
        else:
            try:
                # We are being closed as part of (async) generator shutdown.
                # Use `aclose` to have additional checks for the child to
                # handle shutdown properly.
                if exc_type is GeneratorExit:
                    result = await self.gen.aclose()  # type: ignore
                else:
                    result = await self.gen.athrow(exc_type, exc_val, exc_tb)
            except StopAsyncIteration as exc:
                return exc is not exc_tb
            except RuntimeError as exc:
                if exc is exc_val:
                    return False
                # Handle promotion of unhandled Stop[Async]Iteration to RuntimeError
                if isinstance(exc_val, (StopIteration, StopAsyncIteration)):
                    if exc.__cause__ is exc_val:
                        return False
                raise
            except exc_type as exc:
                if exc is not exc_val:
                    raise
                return False
            else:
                # During shutdown, the child generator might be cleaned up early.
                # In this case,
                # - the child will return nothing/None,
                # - we get cleaned up via GeneratorExit as well,
                # and we should go on with our own cleanup.
                # This might happen if the child mishandles GeneratorExit as well,
                # but is the closest we can get to checking the situation.
                # See https://github.com/maxfischer2781/asyncstdlib/issues/84
                if exc_type is GeneratorExit and result is None:
                    return False
                raise RuntimeError("generator did not stop after throw() in __aexit__")


@public_module(__name__, "closing")
class Closing(Generic[AC]):
    """
    Create an :term:`asynchronous context manager` to ``aclose`` some ``thing`` on exit

    Once entered, the context manager guarantees to ``await thing.aclose()``
    at the end of its block. This is useful for safe cleanup even if errors
    occur.

    Use :py:class:`~.closing` for objects that need reliable cleanup but do not support
    the context manager protocol. For example, it is advisable to prompty clean up any
    :term:`asynchronous iterator` that holds resources:

    .. code-block:: python3

        import asyncstdlib as a

        async with a.closing(a.iter(something)) as async_iter:
            async for element in async_iter:
                ...

    .. seealso:: Use :py:func:`~.scoped_iter` to ensure an (async) iterable
                 is eventually closed and only :term:`borrowed <borrowing>` until then.
    """

    def __init__(self, thing: AC):
        self.thing = thing

    async def __aenter__(self) -> AC:
        return self.thing

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        await self.thing.aclose()
        return False


closing = Closing


@public_module(__name__, "nullcontext")
class NullContext(Generic[T]):
    """
    Create an :term:`asynchronous context manager` that only returns ``enter_result``

    Intended as a neutral element, a :py:class:`~.nullcontext` serves as a
    placeholder where an async context manager is semantically required
    but not meaningfull. This allows for an optional async context manager with
    a default :py:class:`~.nullcontext`, or to prevent closing of an existing
    context manager in an ``async with`` statement.

    .. code-block:: python3

        async def safe_fetch(source):
            if not isinstance(source, AsyncIterator):
                # use a context manager if required ...
                acm = a.closing(iter(source))
            else:
                # ... or a neutral placeholder
                acm = a.nullcontext(source)
            async with acm as async_iter:
                ...
    """

    __slots__ = ("enter_result",)

    @overload
    def __init__(self: "NullContext[None]", enter_result: None = ...) -> None:
        ...

    @overload
    def __init__(self: "NullContext[T]", enter_result: T) -> None:
        ...

    def __init__(self, enter_result: Optional[T] = None):
        self.enter_result = enter_result

    @overload
    async def __aenter__(self: "NullContext[None]") -> None:
        ...

    @overload
    async def __aenter__(self: "NullContext[T]") -> T:
        ...

    async def __aenter__(self) -> Optional[T]:
        return self.enter_result

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        return False


nullcontext = NullContext


SE = TypeVar(
    "SE",
    bound=Union[
        AsyncContextManager[Any],
        ContextManager[Any],
        Callable[[Any, BaseException, Any], Optional[bool]],
        Callable[[Any, BaseException, Any], Awaitable[Optional[bool]]],
    ],
)


class ExitStack:
    """
    Context Manager emulating several nested Context Managers

    Once an :py:class:`~.ExitStack` is entered, :py:meth:`enter_context` can be used to
    emulate entering further context managers. When unwinding the stack, context
    managers are exited in LIFO order, effectively emulating nested context managers.
    The primary use-case is programmatically entering optional or a dynamically sized
    number of context managers.

    In addition, arbitrary cleanup functions and callbacks can be registered using
    :py:meth:`push` and :py:meth:`callback`. This allows running additional cleanup,
    similar to ``defer`` statements in other languages.

    .. note::

        Unlike :py:class:`contextlib.AsyncExitStack`, this class provides
        an :term:`async neutral` version of the :py:class:`contextlib.ExitStack`.
        There are no separate methods to distinguish async and regular arguments.
    """

    def __init__(self) -> None:
        self._exit_callbacks: Deque[Callable[..., Awaitable[Optional[bool]]]] = deque()

    @staticmethod
    async def _aexit_callback(
        callback: Callable[[], Awaitable[Any]], exc_type: Any, exc_val: Any, tb: Any
    ) -> bool:
        """Invoke a callback as if it were an ``__aexit__`` method"""
        await callback()
        return False  # callbacks never suppress exceptions

    def pop_all(self) -> "ExitStack":
        """
        Transfer all exit callbacks to a new :py:class:`~.ExitStack`

        :return: new :py:class:`~.ExitStack` owning all previously registered callbacks

        The responsibility of invoking previously registered handlers is fully
        transferred to the new :py:class:`~.ExitStack`. Neither calling this method,
        nor closing the original :py:class:`~.ExitStack` (via :py:meth:`~.aclose`
        or an ``async with`` statement) invokes these callbacks. Note that callbacks
        added after calling :py:meth:`~.pop_all` are not affected by this.
        """
        new_stack = type(self)()
        new_stack._exit_callbacks, self._exit_callbacks = self._exit_callbacks, deque()
        return new_stack

    def push(self, exit: SE) -> SE:
        """
        Registers a callback with the standard ``__aexit__`` method signature

        :param exit: the exit callback to invoke on ``__aexit__``
        :return: the ``exit`` parameter, unchanged

        When the stack is unwound, callbacks receive the current exception details, and
        are expected to return :py:data:`True` if the exception should be suppressed.
        Two normalizations are applied to match the ``__aexit__`` signature:

        * If ``exit`` has an ``__aexit__`` method, this method is used instead.

        * If ``exit`` has an ``__exit__`` method, this method is used instead.
          It is automatically treated as asynchronous.

        * If ``exit`` is not asynchronous, it is automatically treated as such.

        Note that ``exit`` is only treated as :term:`async neutral` when it does not
        have an ``__aexit__`` method. If an ``__aexit__`` method is found, it is
        expected to conform to the :py:meth:`object.__aexit__` signature.

        Regardless of internal normalizations, ``exit`` is always returned unchanged.
        This allows using ``push`` as a decorator.

        .. seealso::

            When receiving a context manager, this method only sets up ``__aexit__`` or
            ``__exit__`` for being called. It does not *enter* the context manager.
            If a context manager must also be entered, use :py:meth:`~.enter_context`
            instead.
        """
        try:
            aexit = _slot_get(exit, "__aexit__")
        except AttributeError:
            try:
                aexit = awaitify(_slot_get(exit, "__exit__"))
            except AttributeError:
                assert callable(
                    exit
                ), f"Expected (async) context manager or callable, got {exit}"
                aexit = awaitify(exit)
        self._exit_callbacks.append(aexit)
        return exit

    def callback(self, callback: C, *args: Any, **kwargs: Any) -> C:
        """
        Registers an arbitrary callback to be called with arguments on unwinding

        :return: the ``callback`` parameter, unchanged

        The callback is invoked as ``await callback(*args, **kwargs)`` when the stack
        unwinds. It does not receive the current exception details and cannot suppress
        the exception handled by the stack. The callback is treated as
        :term:`async neutral`, i.e. it may be a synchronous function.

        This method does not change its argument, and can be used as a context manager.
        """
        self._exit_callbacks.append(
            partial(self._aexit_callback, partial(awaitify(callback), *args, **kwargs))
        )
        return callback

    async def enter_context(self, cm: AnyContextManager[T]) -> T:
        """
        Enter the supplied context manager, and register it for exit if successful

        This method is equivalent to using ``cm`` in an ``async with`` statement;
        if ``cm`` can only be used in a ``with`` statement, it is silently promoted.
        The stack will enter ``cm`` and, if successful, ensure that ``cm`` is exited
        when the stack unwinds. The return value of this method is the value that
        ``cm`` provides in an ``async with`` statement.

        .. code-block:: python3

            # explicitly enter context managers
            async with cm_a as value_a, cm_b as value_b:
                ...

            # programmatically enter context managers
            async with a.ExitStack() as exit_stack:
                value_a = exit_stack.enter_context(cm_a)
                value_b = exit_stack.enter_context(cm_b)
                ...

        When unwinding, the context manager is exited as if it were part of a regular
        stack of ``async with`` (that is, in LIFO order). It receives the current
        exception details and may suppress it as usual.
        As with the ``async with`` statement, if the context cannot be entered
        (that is, ``await cm.__aenter__()`` throws an exception) it is not exited
        either.
        """
        try:
            aexit = _slot_get(cm, "__aexit__")
        except AttributeError:
            aexit = awaitify(_slot_get(cm, "__exit__"))
            context_value = _slot_get(cm, "__enter__")()
        else:
            context_value = await _slot_get(cm, "__aenter__")()
        self._exit_callbacks.append(aexit)
        return context_value  # type: ignore

    async def aclose(self) -> None:
        """
        Immediately unwind the context stack

        .. note::

            Unlike the regular :py:meth:`contextlib.ExitStack.close` method,
            this method is ``async`` and follows the ``aclose`` naming convention.
        """
        await self.__aexit__(None, None, None)

    @staticmethod
    def _stitch_context(
        exception: BaseException,
        context: BaseException,
        base_context: Optional[BaseException],
    ) -> None:
        """
        Emulate that `exception` was caused by an unhandled `context`

        :param exception: the exception to adjust
        :param context: the context
        :param base_context: the latest context we would adjust
        """
        # we may have receive a child exception of the one that needs stitching
        # walk the contexts until we reach a root exception (no context) or our
        # own base context
        exc_context = exception.__context__
        while exc_context is not None and exc_context is not base_context:
            if exc_context is context:
                return
            exception = exc_context
            exc_context = exception.__context__
        # Change the end of the chain to point to the exception
        # we expect it to reference
        exception.__context__ = context

    async def __aenter__(self) -> "ExitStack":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, tb: Any) -> bool:
        received_exc = exc_type is not None
        # Even if we don't handle an exception *right now*, we may be part
        # of an exception handler unwinding gracefully. This is our __context__.
        unwind_context = sys.exc_info()[1]
        suppress_exc = False
        reraise_exc = False
        # Callbacks are invoked in LIFO order to match nested context managers
        for callback in reversed(self._exit_callbacks):
            try:
                if await callback(exc_type, exc_val, tb):
                    suppress_exc = True
                    reraise_exc = False
                    exc_type = exc_val = tb = None
            except BaseException as exc:
                # simulate the stack of exceptions by setting the context
                self._stitch_context(exc, exc_val, unwind_context)
                reraise_exc = True
                exc_type, exc_val, tb = type(exc), exc, exc.__traceback__
        if reraise_exc and exc_val is not None:
            # The __context__ is replaced by a normal `raise`, and only
            # preserved by a bare `raise` in an except block.
            exc_context = exc_val.__context__
            try:
                raise exc_val
            except BaseException:
                exc_val.__context__ = exc_context
                raise
        return received_exc and suppress_exc
