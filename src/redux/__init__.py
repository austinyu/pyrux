"""Redux-like state management library for Python."""

__all__ = [
    "Slice",
    "Store",
    "reduce",
    "extra_reduce",
    "create_store",
    "get_state",
    "get_slice",
    "get_store",
    "dispatch",
    "dispatch_slice",
    "dispatch_state",
    "subscribe",
    "force_notify",
    "build_path",
]

from .slice import Slice, build_path
from .store import (
    Store,
    create_store,
    dispatch,
    dispatch_slice,
    dispatch_state,
    extra_reduce,
    force_notify,
    get_slice,
    get_state,
    get_store,
    reduce,
    subscribe,
)
