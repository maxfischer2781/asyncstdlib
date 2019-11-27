from typing import TypeVar

T = TypeVar("T")


def public_module(module_fqdn: str):
    """Set the module name of a function or class"""

    def decorator(thing: T) -> T:
        thing.__module__ = module_fqdn
        return thing

    return decorator
