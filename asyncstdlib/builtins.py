from typing import (
    Iterable,
    AsyncIterable,
    Union,
    AsyncIterator,
    TypeVar,
    Awaitable,
    Callable,
    Tuple,
    List,
    Set,
    Optional,
    Dict,
    Any,
)

from typing_extensions import Protocol

from ._core import iter, AnyIterable


T = TypeVar("T", contravariant=True)
R = TypeVar("R", covariant=True)


class Sentinel:
    """Placeholder with configurable ``repr``"""

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


async def all(iterable: AnyIterable[T]) -> bool:
    """
    Return :py:data:`True` if none of the elements of the (async) ``iterable`` are false
    """
    async for element in iter(iterable):
        if not element:
            return False
    return True


async def any(iterable: AnyIterable[T]) -> bool:
    """
    Return :py:data:`False` if none of the elements of the (async) ``iterable`` are true
    """
    async for element in iter(iterable):
        if element:
            return True
    return False


async def zip(*iterables: AnyIterable[T]) -> AsyncIterator[Tuple[T, ...]]:
    """
    Create an async iterator that aggregates elements from each of the (async) iterables

    The next element of ``zip`` is a :py:class:`tuple` of the next element of
    each of its ``iterables``. As soon as any of its ``iterables`` is exhausted,
    ``zip`` is exhausted as well. This means that if ``zip`` receives *n* ``iterables``,
    with the shortest having *m* elements, it becomes a generator *m*-times producing
    an *n*-tuple.

    .. code:: python3

        async for va, vb, vc in zip(a, b, c):
            print(f'a => {va}, b => {vb}, c => {vc}'

    If ``iterables`` is empty, the ``zip`` iterator is empty as well.
    Multiple ``iterables`` may be mixed regular and async iterables.
    """
    if not iterables:
        return
    aiters = (*(iter(it) for it in iterables),)
    try:
        while True:
            yield (*[await anext(it) for it in aiters],)
    except StopAsyncIteration:
        return


class SyncVariadic(Protocol[T, R]):
    """Type of a ``def`` function taking any number of arguments"""

    def __call__(self, *args: T) -> R:
        ...


class AsyncVariadic(Protocol[T, R]):
    """Type of an ``async def`` function taking any number of arguments"""

    def __call__(self, *args: T) -> Awaitable[R]:
        ...


async def map(
    function: Union[SyncVariadic, AsyncVariadic], *iterable: AnyIterable[T],
) -> AsyncIterator[R]:
    r"""
    An async iterator mapping an (async) function to items from (async) iterables

    At each step, ``map`` collects the next item from each iterable and calls
    ``function`` with all items; if ``function`` provides an awaitable,
    it is ``await``\ ed. The result is the next value of ``map``.
    Barring sync/async translation, ``map`` is equivalent to
    ``(await function(*args) async for args in zip(iterables))``.

    It is important that ``func`` receives *one* item from *each*  iterable at
    every step. For *n* ``iterable``, ``func`` must take *n* positional arguments.
    Similar to :py:func:`~.zip`, ``map`` is exhausted as soon as its
    *first* argument is exhausted.

    The ``function`` may be a regular or async callable.
    Multiple ``iterable`` may be mixed regular and async iterables.
    """
    args_iter = zip(*iterable)
    args = await anext(args_iter)
    result = function(*args)
    if isinstance(result, Awaitable):
        yield await result
        async for args in args_iter:
            result = function(*args)
            yield await result
    else:
        yield result
        async for args in args_iter:
            result = function(*args)
            yield result


__MAX_DEFAULT = Sentinel("<no default>")


async def max(
    iterable: AnyIterable[T],
    *,
    key: Optional[Callable[[T], Any]] = None,
    default: T = __MAX_DEFAULT,
) -> T:
    """
    Return the largest item from an (async) iterable or from two or more values

    :raises ValueError: if ``iterable`` is empty and ``default`` is not set

    The ``key`` argument specifies a one-argument ordering function like that used
    for :py:meth:`list.sort`. It may be a regular or async callable and defaults to
    the identity function. The ``default`` argument specifies an object to return
    if the provided ``iterable`` is empty. If the ``iterable`` is empty and
    ``default`` is not provided, a :py:exc:`ValueError` is raised.

    .. note::

        The two-or-more-arguments variant is not supported yet.
    """
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


async def min(
    iterable: AnyIterable[T],
    *,
    key: Optional[Callable[[T], Any]] = None,
    default: T = __MAX_DEFAULT,
) -> T:
    """
    Return the smallest item from an (async) iterable or from two or more values

    :raises ValueError: if ``iterable`` is empty and ``default`` is not set

    The ``key`` argument specifies a one-argument ordering function like that used
    for :py:meth:`list.sort`. It may be a regular or async callable and defaults to
    the identity function. The ``default`` argument specifies an object to return
    if the provided ``iterable`` is empty. If the ``iterable`` is empty and
    ``default`` is not provided, a :py:exc:`ValueError` is raised.

    .. note::

        The two-or-more-arguments variant is not supported yet.
    """
    item_iter = iter(iterable)
    best = await anext(item_iter, default=__MAX_DEFAULT)
    if best is __MAX_DEFAULT:
        if default is __MAX_DEFAULT:
            raise ValueError("max() arg is an empty sequence")
        return default
    if key is None:
        async for item in item_iter:
            if item < best:
                best = item
    else:
        best_key = key(best)
        if isinstance(best_key, Awaitable):
            best_key = await best_key
            async for item in item_iter:
                item_key = await key(item)
                if item_key < best_key:
                    best = item
                    best_key = item_key
        else:
            async for item in item_iter:
                item_key = key(item)
                if item_key < best_key:
                    best = item
                    best_key = item_key
    return best


async def filter(
    function: Union[Callable[[T], bool], Callable[[T], Awaitable[bool]], None],
    iterable: AnyIterable[T],
) -> AsyncIterator[T]:
    """
    An async iterator of elements in an (async) iterable filtered by an (async) callable

    Barring sync/async translation, ``filter`` is equivalent to
    ``(element async for args in iterable if await func(element))``.

    The ``function`` may be a regular or async callable.
    The ``iterable`` may be a regular or async iterable.
    """
    if function is None:
        async for item in iter(iterable):
            if item:
                yield item
    else:
        item_iter = iter(iterable)
        item = await anext(item_iter)
        result = function(item)
        if isinstance(result, Awaitable):
            if await result:
                yield item
            del result
            async for item in item_iter:
                if await function(item):  # type: ignore
                    yield item
        else:
            if result:
                yield item
            del result
            async for item in item_iter:
                if function(item):
                    yield item


async def enumerate(iterable: AnyIterable[T], start=0) -> AsyncIterator[Tuple[int, T]]:
    """
    An async iterator of a tuple of count and element in an (async) iterable

    The ``iterable`` may be a regular or async iterable.
    """
    count = start
    async for item in iter(iterable):
        yield count, item
        count += 1


async def sum(iterable: AnyIterable[T], start: T = 0) -> T:
    """
    Sum of ``start`` and all elements in the (async) iterable
    """
    total = start
    async for item in iter(iterable):
        total += item
    return total


async def list(iterable: Union[Iterable[T], AsyncIterable[T], None] = None) -> List[T]:
    """
    Create a :py:class:`list` from an (async) iterable
    """
    if iterable is None:
        return []
    return [element async for element in iter(iterable)]


async def tuple(
    iterable: Union[Iterable[T], AsyncIterable[T], None] = None
) -> Tuple[T, ...]:
    """
    Create a :py:class:`tuple` from an (async) iterable
    """
    if iterable is None:
        return ()
    return (*[element async for element in iter(iterable)],)


async def dict(
    iterable: Union[Iterable[Tuple[str, T]], AsyncIterable[Tuple[str, T]], None] = None,
    **kwargs: T,
) -> Dict[str, T]:
    """
    Create a :py:class:`dict` from an (async) iterable
    """
    if iterable is None:
        return {**kwargs}
    base_dict = {key: value async for key, value in iter(iterable)}
    if kwargs:
        base_dict.update(kwargs)
    return base_dict


async def set(iterable: Union[Iterable[T], AsyncIterable[T], None] = None) -> Set[T]:
    """
    Create a :py:class:`set` from an (async) iterable
    """
    if iterable is None:
        return {a for a in ()}  # type: ignore
    return {element async for element in iter(iterable)}
