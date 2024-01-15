from asyncstdlib import _core

from .utility import sync


@sync
async def test_scoped_iter_graceful():
    """Test that ScopedIter handlers non-generator iterables"""

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
        # check that the iterator satisfies iter(iterator) is iterator
        assert _core.aiter(async_iterator) is async_iterator
        assert (await async_iterator.__anext__()) == 1
    assert (await async_iterator.__anext__()) == 1
