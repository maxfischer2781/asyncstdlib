from typing import TypeVar, Optional, Callable

from ._typing import Protocol


class Definition(Protocol):
    """
    Type of objects created from a class or function definition
    """

    __name__: str
    __module__: str
    __qualname__: str


D = TypeVar("D", bound=Definition)


def public_module(
    module_name: str, qual_name: Optional[str] = None
) -> Callable[[D], D]:
    """Set the module name of a function or class"""

    def decorator(thing: D) -> D:
        thing.__module__ = module_name
        if qual_name is not None:
            thing.__qualname__ = qual_name
            thing.__name__ = qual_name.rpartition(".")[-1]
        return thing

    return decorator
