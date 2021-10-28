from typing import (
    Iterable,
    AsyncIterable,
    Union,
    AsyncIterator,
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
import builtins as _sync_builtins

from ._typing import T, T1, T2, T3, T4, T5, R, HK, LT, ADD, AnyIterable
from ._core import (
    aiter,
    ScopedIter,
    awaitify as _awaitify,
    Sentinel,
)


__ANEXT_DEFAULT = Sentinel("<no default>")


@overload
async def anext(iterator: AsyncIterator[T]) -> T:
    ...


@overload
async def anext(iterator: AsyncIterator[T], default: T) -> T:
    ...


async def anext(
    iterator: AsyncIterator[T], default: Union[Sentinel, T] = __ANEXT_DEFAULT
) -> T:
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
        return default  # type: ignore


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
        return aiter(subject)  # type: ignore
    elif not callable(subject):
        raise TypeError("iter(v, w): v must be callable")
    else:
        assert not isinstance(sentinel, Sentinel)
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


@overload
def zip(
    __it1: AnyIterable[T1],
    *,
    strict: bool = ...,
) -> AsyncIterator[Tuple[T1]]:
    ...


@overload
def zip(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    *,
    strict: bool = ...,
) -> AsyncIterator[Tuple[T1, T2]]:
    ...


@overload
def zip(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    *,
    strict: bool = ...,
) -> AsyncIterator[Tuple[T1, T2, T3]]:
    ...


@overload
def zip(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    *,
    strict: bool = ...,
) -> AsyncIterator[Tuple[T1, T2, T3, T4]]:
    ...


@overload
def zip(
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    __it5: AnyIterable[T5],
    *,
    strict: bool = ...,
) -> AsyncIterator[Tuple[T1, T2, T3, T4, T5]]:
    ...


@overload
def zip(
    __it1: AnyIterable[Any],
    __it2: AnyIterable[Any],
    __it3: AnyIterable[Any],
    __it4: AnyIterable[Any],
    __it5: AnyIterable[Any],
    *iterables: AnyIterable[Any],
    strict: bool = ...,
) -> AsyncIterator[Tuple[Any, ...]]:
    ...


async def zip(
    *iterables: AnyIterable[Any], strict: bool = False
) -> AsyncIterator[Tuple[Any, ...]]:
    """
    Create an async iterator that aggregates elements from each of the (async) iterables

    :raises ValueError: if the ``iterables`` are not equal length and ``strict`` is set

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

    When called with ``strict=True``, all ``iterables`` must be of same length;
    in this mode ``zip`` raises :py:exc:`ValueError` if any ``iterables`` are not
    exhausted with the others.
    """
    if not iterables:
        return
    aiters = (*(aiter(it) for it in iterables),)
    del iterables
    try:
        inner = _zip_inner(aiters) if not strict else _zip_inner_strict(aiters)
        async for items in inner:
            yield items
    finally:
        for iterator in aiters:
            try:
                aclose = iterator.aclose  # type: ignore
            except AttributeError:
                pass
            else:
                await aclose()


async def _zip_inner(
    aiters: Tuple[AsyncIterator[T], ...]
) -> AsyncIterator[Tuple[T, ...]]:
    """Direct zip transposing tuple-of-iterators to iterator-of-tuples"""
    try:
        while True:
            yield (*[await anext(it) for it in aiters],)
    except StopAsyncIteration:
        return


async def _zip_inner_strict(
    aiters: Tuple[AsyncIterator[T], ...]
) -> AsyncIterator[Tuple[T, ...]]:
    """Length aware zip checking that all iterators are equal length"""
    # track index of the last iterator we tried to anext
    tried = 0
    try:
        while True:
            items = []
            for tried, _aiter in _sync_builtins.enumerate(aiters):  # noqa: B007
                items.append(await anext(_aiter))
            yield (*items,)
    except StopAsyncIteration:
        # after the first iterable provided an item, some later iterable was empty
        if tried > 0:
            plural = " " if tried == 1 else "s 1-"
            raise ValueError(
                f"zip() argument {tried+1} is shorter than argument{plural}{tried}"
            ) from None
        # after the first iterable was empty, some later iterable may be not
        sentinel = object()
        for tried, _aiter in _sync_builtins.enumerate(aiters):
            if await anext(_aiter, sentinel) is not sentinel:
                plural = " " if tried == 1 else "s 1-"
                raise ValueError(
                    f"zip() argument {tried+1} is longer than argument{plural}{tried}"
                ) from None
        return


@overload
def map(
    function: Callable[[T1], Awaitable[R]],
    __it1: AnyIterable[T1],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[[T1], R],
    __it1: AnyIterable[T1],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[[T1, T2], Awaitable[R]],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[[T1, T2], R], __it1: AnyIterable[T1], __it2: AnyIterable[T2]
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[[T1, T2, T3], Awaitable[R]],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[[T1, T2, T3], R],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[[T1, T2, T3, T4], Awaitable[R]],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[[T1, T2, T3, T4], R],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[[T1, T2, T3, T4, T5], Awaitable[R]],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    __it5: AnyIterable[T5],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[[T1, T2, T3, T4, T5], R],
    __it1: AnyIterable[T1],
    __it2: AnyIterable[T2],
    __it3: AnyIterable[T3],
    __it4: AnyIterable[T4],
    __it5: AnyIterable[T5],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[..., Awaitable[R]],
    __it1: AnyIterable[Any],
    __it2: AnyIterable[Any],
    __it3: AnyIterable[Any],
    __it4: AnyIterable[Any],
    __it5: AnyIterable[Any],
    *iterable: AnyIterable[Any],
) -> AsyncIterator[R]:
    ...


@overload
def map(
    function: Callable[..., R],
    __it1: AnyIterable[Any],
    __it2: AnyIterable[Any],
    __it3: AnyIterable[Any],
    __it4: AnyIterable[Any],
    __it5: AnyIterable[Any],
    *iterable: AnyIterable[Any],
) -> AsyncIterator[R]:
    ...


async def map(
    function: Union[Callable[..., R], Callable[..., Awaitable[R]]],
    *iterable: AnyIterable[Any],
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


__MIN_MAX_DEFAULT = Sentinel("<no default>")


@overload
async def max(iterable: AnyIterable[LT], *, key: None = ...) -> LT:
    ...


@overload
async def max(
    iterable: AnyIterable[LT], *, key: None = ..., default: T
) -> Union[LT, T]:
    ...


@overload
async def max(iterable: AnyIterable[T1], *, key: Callable[[T1], LT] = ...) -> T1:
    ...


@overload
async def max(
    iterable: AnyIterable[T1], *, key: Callable[[T1], LT] = ..., default: T2
) -> Union[T1, T2]:
    ...


async def max(
    iterable: AnyIterable[Any],
    *,
    key: Optional[Callable[[Any], Any]] = None,
    default: Any = __MIN_MAX_DEFAULT,
) -> Any:
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
    return await _min_max(iterable, key, True, default)


@overload
async def min(iterable: AnyIterable[LT], *, key: None = ...) -> LT:
    ...


@overload
async def min(
    iterable: AnyIterable[LT], *, key: None = ..., default: T
) -> Union[LT, T]:
    ...


@overload
async def min(iterable: AnyIterable[T1], *, key: Callable[[T1], LT] = ...) -> T1:
    ...


@overload
async def min(
    iterable: AnyIterable[T1], *, key: Callable[[T1], LT] = ..., default: T2
) -> Union[T1, T2]:
    ...


async def min(
    iterable: AnyIterable[Any],
    *,
    key: Optional[Callable[[Any], Any]] = None,
    default: Any = __MIN_MAX_DEFAULT,
) -> Any:
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
    return await _min_max(iterable, key, False, default)


async def _min_max(
    iterable: AnyIterable[LT],
    key: Optional[Callable[[LT], Any]],
    invert: bool,
    default: LT = __MIN_MAX_DEFAULT,  # type: ignore
) -> LT:
    """
    Implementation of ``min``/``max``

    :param invert: compute ``max`` if ``True`` and ``min`` otherwise
    """
    async with ScopedIter(iterable) as item_iter:
        best = await anext(item_iter, default=default)
        # this implies that item_iter is empty and default is __MIN_MAX_DEFAULT
        if best is __MIN_MAX_DEFAULT:  # type: ignore
            name = "max" if invert else "min"
            raise ValueError(f"{name}() arg is an empty sequence")
        elif key is None:
            async for item in item_iter:
                if invert ^ (item < best):
                    best = item
        else:
            key = _awaitify(key)
            best_key = await key(best)
            async for item in item_iter:
                item_key = await key(item)
                if invert ^ (item_key < best_key):
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
                if await function(item):
                    yield item


async def enumerate(
    iterable: AnyIterable[T], start: int = 0
) -> AsyncIterator[Tuple[int, T]]:
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


@overload
async def sum(iterable: AnyIterable[int]) -> int:
    ...


@overload
async def sum(iterable: AnyIterable[float]) -> float:
    ...


@overload
async def sum(iterable: AnyIterable[ADD], start: ADD) -> ADD:
    ...


async def sum(iterable: AnyIterable[Any], start: Any = 0) -> Any:
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
    iterable: Union[Iterable[Tuple[HK, T]], AsyncIterable[Tuple[HK, T]]] = (),
) -> Dict[HK, T]:
    pass


@overload  # noqa: F811
async def dict(  # noqa: F811
    iterable: Union[Iterable[Tuple[HK, T]], AsyncIterable[Tuple[HK, T]]] = (),
    **kwargs: T,
) -> Dict[Union[HK, str], T]:
    pass


async def dict(  # noqa: F811
    iterable: Union[Iterable[Tuple[HK, T]], AsyncIterable[Tuple[HK, T]]] = (),
    **kwargs: T,
) -> Dict[Any, T]:
    """
    Create a :py:class:`dict` from an (async) iterable and keywords

    This is equivalent to ``{key: value async for key, value in iterable}``
    if no keywords are provided.
    """
    if not iterable:
        return {**kwargs}
    base_dict: Dict[Any, T] = {key: value async for key, value in aiter(iterable)}
    if kwargs:
        base_dict.update(kwargs)
    return base_dict


async def set(iterable: Union[Iterable[T], AsyncIterable[T]] = ()) -> Set[T]:
    """
    Create a :py:class:`set` from an (async) iterable

    This is equivalent to ``{element async for element in iterable}``.
    """
    return {element async for element in aiter(iterable)}


@overload
async def sorted(
    iterable: AnyIterable[LT], *, key: None = ..., reverse: bool = ...
) -> List[LT]:
    ...


@overload
async def sorted(
    iterable: AnyIterable[T], *, key: Callable[[T], LT], reverse: bool = ...
) -> List[T]:
    ...


async def sorted(
    iterable: AnyIterable[T],
    *,
    key: Optional[Callable[[T], LT]] = None,
    reverse: bool = False,
) -> List[T]:
    """
    Sort items from an (async) iterable into a new list

    The optional ``key`` argument specifies a one-argument (async) callable, which
    provides a substitute for determining the sort order of each item.
    The special value and default :py:data:`None` represents the identity functions,
    i.e. compares items directly.

    The default sort order is ascending, that is items with ``a < b``
    imply ``result.index(a) < result.index(b)``. Use ``reverse=True``
    for descending sort order.

    .. note::

        The actual sorting is synchronous,
        so a very large ``iterable`` or very slow comparison
        may block the event loop notably.
        It is guaranteed to be worst-case O(n log n) runtime.
    """
    if key is None:
        # TODO: is this a worthwhile optimisation?
        try:
            return _sync_builtins.sorted(iterable, reverse=reverse)  # type: ignore
        except TypeError:
            items = [item async for item in aiter(iterable)]
            items.sort(reverse=reverse)
            return items
    else:
        async_key = _awaitify(key)
        keyed_items = [(await async_key(item), item) async for item in aiter(iterable)]
        keyed_items.sort(key=lambda ki: ki[0], reverse=reverse)
        return [item for key, item in keyed_items]
