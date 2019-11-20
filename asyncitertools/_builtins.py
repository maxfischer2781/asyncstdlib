from typing import (
    Iterable,
    AsyncIterable,
    Union,
    AsyncIterator,
    TypeVar,
    Awaitable,
    Callable,
    Tuple,
    Optional,
)
from typing_extensions import Protocol


T = TypeVar("T")
R = TypeVar("R")


class Sentinel:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


__ANEXT_DEFAULT = Sentinel("<no default>")


async def anext(iterator: AsyncIterator[T], default=__ANEXT_DEFAULT) -> T:
    try:
        return await iterator.__anext__()
    except StopAsyncIteration:
        if default is __ANEXT_DEFAULT:
            raise
        return default


async def all(iterable: Union[Iterable[T], AsyncIterable[T]]) -> bool:
    async for element in iterable:
        if not element:
            return False
    return True


async def any(iterable: Union[Iterable[T], AsyncIterable[T]]) -> bool:
    async for element in iterable:
        if element:
            return True
    return False


async def zip(
    *iters: Union[Iterable[T], AsyncIterable[T]]
) -> AsyncIterator[Tuple[T, ...]]:
    if not iters:
        return
    aiters = tuple(iter(it) for it in iters)
    print(aiters)
    try:
        while True:
            yield tuple([await anext(it) for it in aiters])
    except StopAsyncIteration:
        return


def iter(source: Union[Iterable[T], AsyncIterable[T]]) -> AsyncIterator[T]:
    if isinstance(source, AsyncIterable):
        return source.__aiter__()
    else:
        return _aiter_sync(source).__aiter__()


async def _aiter_sync(iterable: Iterable):
    for item in iterable:
        yield item


class SyncMapFunc(Protocol[T, R]):
    def __call__(self, *args: T) -> R:
        ...


class AsyncMapFunc(Protocol[T, R]):
    def __call__(self, *args: T) -> Awaitable[R]:
        ...


async def map(
    func: Union[SyncMapFunc, AsyncMapFunc],
    *iterable: Union[Iterable[T], AsyncIterable[T]]
) -> AsyncIterator[R]:
    args_iter = zip(*iterable)
    args = await anext(args_iter)
    result = func(*args)
    if isinstance(result, Awaitable):
        yield await result
        async for args in args_iter:
            result = func(*args)
            yield await result
    else:
        yield result
        async for args in args_iter:
            result = func(*args)
            yield result


__MAX_DEFAULT = Sentinel("<no default>")


async def max(
    iterable: Union[Iterable[T], AsyncIterable[T]],
    *,
    key: Optional[Callable] = None,
    default: T = __MAX_DEFAULT,
) -> T:
    item_iter = iter(iterable)
    best = await anext(item_iter, default=__MAX_DEFAULT)
    if best is __MAX_DEFAULT:
        if default is __MAX_DEFAULT:
            raise ValueError("max() arg is an empty sequence")
        return default
    if key is None:
        async for item in item_iter:
            if item > best:
                best = item
    else:
        best_key = key(best)
        if isinstance(best_key, Awaitable):
            best_key = await best_key
            async for item in item_iter:
                item_key = await key(item)
                if item_key > best_key:
                    best = item
                    best_key = item_key
        else:
            async for item in item_iter:
                item_key = key(item)
                if item_key > best_key:
                    best = item
                    best_key = item_key
    return best


async def filter(
    func: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]], None],
    iterable: Union[Iterable[T], AsyncIterable[T]],
) -> AsyncIterator[T]:
    if func is None:
        async for item in iter(iterable):
            if item:
                yield item
    else:
        item_iter = iter(iterable)
        item = await anext(item_iter)
        result = func(item)
        if isinstance(result, Awaitable):
            if await result:
                yield item
            del result
            async for item in item_iter:
                if await func(item):  # type: ignore
                    yield item
        else:
            if result:
                yield item
            del result
            async for item in item_iter:
                if func(item):
                    yield item


async def enumerate(
    iterable: Union[Iterable[T], AsyncIterable[T]], start=0
) -> AsyncIterator[Tuple[int, T]]:
    count = start
    async for item in iter(iterable):
        yield count, item
        count += 1
