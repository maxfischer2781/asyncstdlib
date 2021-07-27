"""
Helper module to simplify version specific typing imports

This module is for internal use only. Do *not* put any new
"async typing" definitions here.
"""
import sys

if sys.version_info[:2] >= (3, 8):
    from typing import Protocol, AsyncContextManager, ContextManager, TypedDict
else:
    from typing_extensions import (
        Protocol,
        AsyncContextManager,
        ContextManager,
        TypedDict,
    )

__all__ = ["Protocol", "AsyncContextManager", "ContextManager", "TypedDict"]
