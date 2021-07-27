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
