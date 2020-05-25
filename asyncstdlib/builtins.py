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
    overload,
)

from typing_extensions import Protocol

from ._core import (
    aiter,
    AnyIterable,
    ScopedIter,
    awaitify as _awaitify,
    Sentinel,
)


T = TypeVar("T", contravariant=True)
K = TypeVar("K")
R = TypeVar("R", covariant=True)

__ANEXT_DEFAULT = Sentinel("<no default>")


async def anext(iterator: AsyncIterator[T], default=__ANEXT_DEFAULT) -> T:
    """
    Retrieve the next item from the async iterator

    :raises StopAsyncIteration: if ``iterator`` is exhausted and ``default`` is not set

    If ``default`` is given, it is returned if the ``iterator`` is exhausted.
    Otherwise, :py:exc:`StopAsyncIteration` is raised for an exhausted ``iterator``.

    .. note::

        This function is not :term:`async neutral`.
        The ``iterator`` must be an :term:`asynchronous iterator`,
        i.e. support the :py:meth:`~object.__anext__` method.
    """
    try:
        return await iterator.__anext__()
    except StopAsyncIteration:
        if default is __ANEXT_DEFAULT:
            raise
        return default


__ITER_DEFAULT = Sentinel("<no default>")


@overload
def iter(subject: AnyIterable[T]) -> AsyncIterator[T]:
    pass


@overload
def iter(subject: Callable[[], Awaitable[T]], sentinel: T) -> AsyncIterator[T]:
    pass


def iter(
    subject: Union[AnyIterable[T], Callable[[], Awaitable[T]]],
    sentinel: Union[Sentinel, T] = __ITER_DEFAULT,
) -> AsyncIterator[T]:
    """
    An async iterator object yielding elements from ``subject``

    :raises TypeError: if ``subject`` does not support any iteration protocol

    If ``sentinel`` is not given, the ``subject`` must support
    the async iteration protocol (the :py:meth:`~object.__aiter__` method),
    the regular iteration protocol (the :py:meth:`~object.__iter__` method),
    or it must support the sequence protocol (the :py:meth:`~object.__getitem__`
    method with integer arguments starting at 0).
    In either case, an async iterator is returned.

    If ``sentinel`` is given, subject must be an (async) callable. In this case,
    :py:func:`~.iter` provides an async iterator that uses ``await subject()``
    to produce new values. Once a value equals ``sentinel``, the value is discarded
    and iteration stops.

    .. seealso:: Use :py:func:`~.scoped_iter` to ensure an (async) iterable
                 is eventually closed and only :term:`borrowed <borrowing>` until then.
    """
    if sentinel is __ITER_DEFAULT:
        return aiter(subject)
    elif not callable(subject):
        raise TypeError("iter(v, w): v must be callable")
    else:
        return acallable_iterator(subject, sentinel)


async def acallable_iterator(
    subject: Callable[[], Awaitable[T]], sentinel: T
) -> AsyncIterator[T]:
    subject = _awaitify(subject)
    value = await subject()
    while value != sentinel:
        yield value
        value = await subject()


async def all(iterable: AnyIterable[T]) -> bool:
    """
    Return :py:data:`True` if none of the elements of the (async) ``iterable`` are false
    """
    async with ScopedIter(iterable) as item_iter:
        async for element in item_iter:
            if not element:
                return False
        return True


async def any(iterable: AnyIterable[T]) -> bool:
    """
    Return :py:data:`False` if none of the elements of the (async) ``iterable`` are true
    """
    async with ScopedIter(iterable) as item_iter:
        async for element in item_iter:
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
    aiters = (*(aiter(it) for it in iterables),)
    del iterables
    try:
        while True:
            yield (*[await anext(it) for it in aiters],)
    except StopAsyncIteration:
        return
    finally:
        for iterator in aiters:
            try:
                aclose = iterator.aclose()
            except AttributeError:
                pass
            else:
                await aclose


class SyncVariadic(Protocol[T, R]):
    """Type of a ``def`` function taking any number of arguments"""

    def __call__(self, *args: T) -> R:
        raise NotImplementedError


class AsyncVariadic(Protocol[T, R]):
    """Type of an ``async def`` function taking any number of arguments"""

    def __call__(self, *args: T) -> Awaitable[R]:
        raise NotImplementedError


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
    function = _awaitify(function)
    async with ScopedIter(zip(*iterable)) as args_iter:
        async for args in args_iter:
            result = function(*args)
            yield await result


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

        The two-or-more-arguments variant is not supported,
        as it does not benefit from being ``async``.
        Use the builtin :py:func:`max` function instead.
    """
    async with ScopedIter(iterable) as item_iter:
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
            key = _awaitify(key)
            best_key = await key(best)
            async for item in item_iter:
                item_key = await key(item)
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

        The two-or-more-arguments variant is not supported,
        as it does not benefit from being ``async``.
        Use the builtin :py:func:`min` function instead.
    """
    async with ScopedIter(iterable) as item_iter:
        best = await anext(item_iter, default=__MAX_DEFAULT)
        if best is __MAX_DEFAULT:
            if default is __MAX_DEFAULT:
                raise ValueError("min() arg is an empty sequence")
            return default
        if key is None:
            async for item in item_iter:
                if item < best:
                    best = item
        else:
            key = _awaitify(key)
            best_key = await key(best)
            async for item in item_iter:
                item_key = await key(item)
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
    async with ScopedIter(iterable) as item_iter:
        if function is None:
            async for item in item_iter:
                if item:
                    yield item
        else:
            function = _awaitify(function)
            async for item in item_iter:
                if await function(item):  # type: ignore
                    yield item


async def enumerate(iterable: AnyIterable[T], start=0) -> AsyncIterator[Tuple[int, T]]:
    """
    An async iterator of running count and element in an (async) iterable

    The count begins at ``start`` for the first element of ``iterable``,
    and is incremented by ``1`` for each further element.
    The ``iterable`` may be a regular or async iterable.
    """
    count = start
    async with ScopedIter(iterable) as item_iter:
        async for item in item_iter:
            yield count, item
            count += 1


async def sum(iterable: AnyIterable[T], start: T = 0) -> T:
    """
    Sum of ``start`` and all elements in the (async) iterable
    """
    total = start
    async for item in aiter(iterable):
        total += item
    return total


async def list(iterable: Union[Iterable[T], AsyncIterable[T]] = ()) -> List[T]:
    """
    Create a :py:class:`list` from an (async) iterable

    This is equivalent to ``[element async for element in iterable]``.
    """
    return [element async for element in aiter(iterable)]


async def tuple(iterable: Union[Iterable[T], AsyncIterable[T]] = ()) -> Tuple[T, ...]:
    """
    Create a :py:class:`tuple` from an (async) iterable
    """
    return (*[element async for element in aiter(iterable)],)


@overload
async def dict(  # noqa: F811
    iterable: Union[Iterable[Tuple[K, T]], AsyncIterable[Tuple[K, T]]] = (),
) -> Dict[K, T]:
    pass


@overload  # noqa: F811
async def dict(  # noqa: F811
    iterable: Union[Iterable[Tuple[K, T]], AsyncIterable[Tuple[K, T]]] = (),
    **kwargs: T,
) -> Dict[Union[K, str], T]:
    pass


async def dict(  # noqa: F811
    iterable: Union[Iterable[Tuple[K, T]], AsyncIterable[Tuple[K, T]]] = (),
    **kwargs: T,
) -> Dict[Union[K, str], T]:
    """
    Create a :py:class:`dict` from an (async) iterable and keywords

    This is equivalent to ``{key: value async for key, value in iterable}``
    if no keywords are provided.
    """
    if not iterable:
        return {**kwargs}
    base_dict: Dict[Union[K, str], T] = {
        key: value async for key, value in aiter(iterable)
    }
    if kwargs:
        base_dict.update(kwargs)
    return base_dict


async def set(iterable: Union[Iterable[T], AsyncIterable[T]] = ()) -> Set[T]:
    """
    Create a :py:class:`set` from an (async) iterable

    This is equivalent to ``{element async for element in iterable}``.
    """
    return {element async for element in aiter(iterable)}
