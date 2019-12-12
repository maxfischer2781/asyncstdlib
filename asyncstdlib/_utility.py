from typing import TypeVar

T = TypeVar("T")


def public_module(module_name: str, qual_name: str = None):
    """Set the module name of a function or class"""

    def decorator(thing: T) -> T:
        thing.__module__ = module_name
        if qual_name is not None:
            thing.__qualname__ = qual_name
            thing.__name__ = qual_name.rpartition(".")[-1]
        return thing

    return decorator
