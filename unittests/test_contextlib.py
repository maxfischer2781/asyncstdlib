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
    @a.contextmanager
    async def no_yield():
        if False:
            yield

    with pytest.raises(RuntimeError):
        async with no_yield():
            assert False


@sync
async def test_contextmanager_no_stop():
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
        except BaseException:
            yield

    with pytest.raises(RuntimeError):
        async with supress_no_stop():
            raise StopAsyncIteration()


@sync
async def test_contextmanager_raise_asyncstop():
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
            raise StopAsyncIteration("inside")

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
            raise RuntimeError("inside")

    with pytest.raises(RuntimeError, match="inside"):
        async with replace():
            raise RuntimeError("outside")


@sync
async def test_contextmanager_raise_same():
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
        except BaseException as err:
            raise type(err)("inside")

    with pytest.raises(KeyError, match="inside"):
        async with recreate():
            raise KeyError("outside")


@sync
async def test_nullcontext():
    async with a.nullcontext(1337) as value:
        assert value == 1337
