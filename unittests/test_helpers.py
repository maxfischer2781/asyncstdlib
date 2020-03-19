from asyncstdlib import _utility
from asyncstdlib import _core

from .utility import sync


def test_slot_get():
    class Slotted:
        data = 3

        def __neg__(self):
            return -type(self).data

    instance = Slotted()
    assert _utility.slot_get(instance, "data") is instance.data
    assert _utility.slot_get(instance, "__neg__")() == -instance
    assert _utility.slot_get(instance, "__neg__")() == instance.__neg__()
    data, neg = instance.data, -instance
    instance.data = 4
    instance.__neg__ = lambda self: 12
    assert _utility.slot_get(instance, "data") is data
    assert _utility.slot_get(instance, "__neg__")() == neg


@sync
async def test_scoped_iter_graceful():
    class AIterator:
        async def __anext__(self):
            return 1

        def __aiter__(self):
            return self

    class AIterable:
        def __aiter__(self):
            return AIterator()

    async_iterable = AIterable()
    async with _core.ScopedIter(async_iterable) as async_iterator:
        # test that no error from calling the missing `aclose` is thrown
        assert async_iterator is not async_iterable
        assert (await async_iterator.__anext__()) == 1
    assert (await async_iterator.__anext__()) == 1
