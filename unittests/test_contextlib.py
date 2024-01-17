from functools import partial
from contextlib import contextmanager

import pytest

import asyncstdlib as a

from .utility import sync


@sync
async def test_closing():
    class ACloseable:
        def __init__(self):
            self.closed = False

        async def aclose(self):
            self.closed = True

    async with a.closing(ACloseable()) as async_closeable:
        pass
    assert async_closeable.closed


@sync
async def test_contextmanager():
    @a.contextmanager
    async def valid(value):
        yield value

    async with valid(1337) as context:
        assert context == 1337


@sync
async def test_contextmanager_no_yield():
    """Test that it is an error for a context to not yield"""

    @a.contextmanager
    async def no_yield():
        if False:
            yield

    with pytest.raises(RuntimeError):
        async with no_yield():
            assert False


@sync
async def test_contextmanager_no_stop():
    """Test that it is an error for a context to yield again after stopping"""

    @a.contextmanager
    async def no_stop():
        yield
        yield

    with pytest.raises(RuntimeError):
        async with no_stop():
            assert True

    @a.contextmanager
    async def supress_no_stop():
        try:
            yield
        except BaseException:  # noqa: B036
            yield

    with pytest.raises(RuntimeError):
        async with supress_no_stop():
            raise StopAsyncIteration()


@sync
async def test_contextmanager_raise_asyncstop():
    """Test that StopAsyncIteration may propagate out of a context block"""

    @a.contextmanager
    async def no_raise():
        yield

    with pytest.raises(StopAsyncIteration, match="outside"):
        async with no_raise():
            raise StopAsyncIteration("outside")

    @a.contextmanager
    async def replace():
        try:
            yield
        except StopAsyncIteration:
            raise StopAsyncIteration("inside") from None

    with pytest.raises(RuntimeError):
        async with replace():
            raise StopAsyncIteration("outside")


@sync
async def test_contextmanager_raise_runtimeerror():
    @a.contextmanager
    async def no_raise():
        yield

    with pytest.raises(RuntimeError, match="outside"):
        async with no_raise():
            raise RuntimeError("outside")

    @a.contextmanager
    async def replace():
        try:
            yield
        except RuntimeError:
            raise RuntimeError("inside") from None

    with pytest.raises(RuntimeError, match="inside"):
        async with replace():
            raise RuntimeError("outside")


@sync
async def test_contextmanager_raise_same():
    """Test that outer exceptions do not shadow inner/newer ones"""

    @a.contextmanager
    async def reraise():
        try:
            yield
        except BaseException as err:
            raise err

    with pytest.raises(KeyError, match="outside"):
        async with reraise():
            raise KeyError("outside")

    @a.contextmanager
    async def recreate():
        try:
            yield
        except BaseException as err:  # noqa: B036
            raise type(err)("inside") from None

    with pytest.raises(KeyError, match="inside"):
        async with recreate():
            raise KeyError("outside")


@sync
async def test_contextmanager_raise_generatorexit():
    """Test that shutdown via GeneratorExit is propagated"""

    @a.contextmanager
    async def no_op():
        yield

    with pytest.raises(GeneratorExit):
        async with no_op():
            raise GeneratorExit("used to tear down coroutines")

    # during shutdown, generators may be killed in arbitrary order
    # make sure we do not suppress GeneratorExit
    context = no_op()
    with pytest.raises(GeneratorExit, match="inner"):
        async with context:
            # simulate cleanup closing the child early
            await context.gen.aclose()
            raise GeneratorExit("inner")


@sync
async def test_contextmanager_no_suppress_generatorexit():
    """Test that GeneratorExit is not suppressed"""

    @a.contextmanager
    async def no_op():
        yield

    exc = GeneratorExit("GE should not be replaced normally")
    with pytest.raises(type(exc)) as exc_info:
        async with no_op():
            raise exc
    assert exc_info.value is exc

    @a.contextmanager
    async def exit_ge():
        try:
            yield
        except GeneratorExit:
            # treat GE as regular exit
            pass

    with pytest.raises(GeneratorExit):
        async with exit_ge():
            raise GeneratorExit("Resume teardown if child exited")

    @a.contextmanager
    async def ignore_ge():
        try:
            yield
        except GeneratorExit:
            yield

    with pytest.raises(RuntimeError):
        async with ignore_ge():
            raise GeneratorExit("Warn if child does not exit")


@sync
async def test_nullcontext():
    async with a.nullcontext(1337) as value:
        assert value == 1337


class MockAsyncContext:
    def __init__(self, value=None):
        self._value = value
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self._value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited = True


class MockContext:
    def __init__(self, value=None):
        self._value = value
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self._value

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exited = True


@sync
async def test_exist_stack():
    async with a.ExitStack() as exit_stack:
        for value in (0, 1, 2, 3, -5, None, "Hello"):
            assert value == await exit_stack.enter_context(a.nullcontext(value))


@sync
async def test_exit_stack_pop_all():
    async with a.ExitStack() as exit_stack:
        contexts = list(
            map(lambda v: MockAsyncContext(v) if v % 2 else MockContext(v), range(10))
        )
        values = await a.list(a.map(exit_stack.enter_context, contexts))
        assert values == list(range(10))
        assert all(cm.entered for cm in contexts)
        assert all(not cm.exited for cm in contexts)
        clone_stack = exit_stack.pop_all()
    assert all(not cm.exited for cm in contexts)
    await clone_stack.aclose()
    assert all(cm.exited for cm in contexts)


@sync
async def test_exit_stack_callback():
    """Test that callbacks are run regardless of exceptions"""
    unwind_values = []

    async def push(value):
        unwind_values.append(value)
        return True  # attempt to suppress - this must not succeed

    with pytest.raises(KeyError):
        async with a.ExitStack() as exit_stack:
            for value in range(5):
                exit_stack.callback(push, value)
            raise KeyError()
    assert unwind_values == list(reversed(range(5)))


@sync
async def test_exit_stack_push():
    seen = []

    @contextmanager
    def observe():
        try:
            yield
        except BaseException as exc_val:
            seen.append(exc_val)
            raise

    @a.contextmanager
    async def suppress():
        try:
            yield
        except BaseException as exc_val:  # noqa: B036
            seen.append(exc_val)

    async def replace(exc_type, exc_val, tb, new):
        seen.append(exc_val)
        raise new

    with pytest.raises(TypeError) as exc_info:
        async with a.ExitStack() as exit_stack:
            exit_stack.push(partial(replace, new=TypeError()))
            exit_stack.push(partial(replace, new=ValueError()))
            s = suppress()
            await s.__aenter__()
            exit_stack.push(s)
            exit_stack.push(partial(replace, new=IndexError()))
            o = observe()
            o.__enter__()
            exit_stack.push(o)
            raise KeyError()
    assert list(map(type, seen)) == [
        KeyError,
        KeyError,
        IndexError,
        type(None),
        ValueError,
    ]
    assert seen[2].__context__ == seen[1]
    assert exc_info.type == TypeError
    assert exc_info.value.__context__ == seen[-1]


@sync
async def test_exit_stack_stitch_context():
    async def replace(exc_type, exc_val, tb, new):
        try:
            {}["a"]
        except KeyError:
            raise new

    async def extend(exc_type, exc_val, tb, new):
        try:
            raise exc_val
        except exc_type:
            raise new

    replacement_exc, middle_exc, initial_exc = TypeError(), ValueError(), IndexError()
    with pytest.raises(type(replacement_exc)) as exc_info:
        async with a.ExitStack() as exit_stack:
            exit_stack.push(partial(extend, new=replacement_exc))
            exit_stack.push(partial(replace, new=middle_exc))
            raise initial_exc
    assert exc_info.value.__context__ == middle_exc
    assert exc_info.value.__context__.__context__ == initial_exc


@sync
async def test_misuse_enter_context():
    async with a.ExitStack() as exit_stack:
        with pytest.raises(AttributeError):
            await exit_stack.enter_context(None)
    async with a.ExitStack() as exit_stack:
        with pytest.raises(AttributeError) as exc_info:
            try:
                {}[1]
            except KeyError:
                await exit_stack.enter_context(None)
        assert type(exc_info.value.__context__.__context__) is KeyError
