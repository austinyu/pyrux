from __future__ import annotations

from typing import TYPE_CHECKING, TypeVarTuple, Any, overload, TypeVar
from collections.abc import Sequence, Callable

from pyrux.slice import Slice, StatePath


__all__ = [
    "clear_store",
    "create_store",
    "dump_store",
    "load_store",
    "get_store",
    "get_state",
    "dispatch",
    "subscribe",
]

STORE: dict[str, Slice] | None = None

Ts = TypeVarTuple("Ts")
Ts_INTERNAL = TypeVarTuple("Ts_INTERNAL")
T_Slice = TypeVar("T_Slice", bound=Slice)
T_State = TypeVar("T_State")

SubscriptionEntry = tuple[Callable[[tuple], None], list[StatePath]]
SUBSCRIPTIONS: dict[str, dict[str, list[SubscriptionEntry]]] = {}

def clear_store() -> None:
    """Clear the store."""
    global STORE
    assert STORE is not None, "Store not initialized"
    STORE = None

def create_store(slices: Sequence[Slice]) -> None:
    """Create the store with the given slices."""
    global STORE
    assert STORE is None, "Store already initialized"
    STORE = {slice.__class__.__name__: slice for slice in slices}

def dump_store() -> dict[str, Any]:
    """Dump the store to a dictionary."""
    assert STORE is not None, "Store not initialized"
    return {
        slice_name: slice_content.model_dump()
        for slice_name, slice_content in STORE.items()
    }

def load_store(slice_defs: list[type[Slice]], data: dict[str, Any]) -> None:
    """Load the store with the given slice definitions and data."""
    global STORE
    assert STORE is None, "Store already initialized"
    STORE = {}
    for slice_def in slice_defs:
        slice_name = slice_def.__name__
        if slice_name not in data:
            raise KeyError(f"Slice '{slice_name}' not found in data")
        slice_data = data[slice_name]
        if not isinstance(slice_data, dict):
            raise TypeError(f"Slice data for '{slice_name}' must be a dictionary")
        STORE[slice_name] = slice_def.model_validate(slice_data)

def get_store() -> dict[str, Slice]:
    """Get the store."""
    assert STORE is not None, "Store not initialized"
    return STORE

if TYPE_CHECKING:
    def get_state(path: Any) -> Any:
        """Get the state of a specific path."""
        ...

else:

    def get_state(path: StatePath) -> Any:
        """Get the state of a specific path."""
        assert STORE is not None, "Store not initialized"
        slice_name = path.slice_name
        state_name = path.state
        if slice_name not in STORE:
            raise KeyError(f"Slice '{slice_name}' not found in store")
        if state_name not in STORE[slice_name].model_fields_set:
            raise KeyError(f"State '{state_name}' not found in slice '{slice_name}'")
        return STORE[slice_name].get_state(state_name)


if TYPE_CHECKING:
    # For callables that take only one argument (no payload)
    @overload
    def dispatch(
        action_creator: Callable[[T_Slice], T_Slice],
        payload: None = None,
    ) -> None: ...

    # For callables that take two arguments (with payload)
    @overload
    def dispatch(
        action_creator: Callable[[T_Slice, T_State], T_Slice],
        payload: T_State,
    ) -> None: ...

    def dispatch(
        action_creator: Any,
        payload: Any = None,
    ) -> None:
        """"Dispatch an action to the store."""

else:
    Reducer = Callable[[Slice], Slice] | Callable[[Slice, T_State], Slice]

    def dispatch(reducer: Reducer, payload: Any | None = None) -> None:
        assert STORE is not None, "Store not initialized"
        slice_name = reducer.__qualname__.split(".")[0]
        if payload is None:
            new_slice = reducer(STORE[slice_name])
        else:
            new_slice = reducer(STORE[slice_name], payload)
        slice_state_names = new_slice.model_fields_set
        for state_name in slice_state_names:
            new_state = new_slice.get_state(state_name)
            if (
                STORE[slice_name].get_state(state_name) != new_state  # state changed
                and slice_name in SUBSCRIPTIONS  # has subscribers for this slice
                and state_name in SUBSCRIPTIONS[slice_name]  # has subscribers for this state
            ):
                for callback, paths in SUBSCRIPTIONS[slice_name][state_name]:
                    callback(
                        tuple(
                            get_state(path) if path.state != state_name else new_state
                            for path in paths
                        )
                    )

        STORE[slice_name] = new_slice


if TYPE_CHECKING:

    @overload
    def subscribe(
        args: tuple[*Ts],
    ) -> Callable[[Callable[[tuple[*Ts]], None]], Callable[[], None]]: ...

    @overload
    def subscribe(
        args: T_State,
    ) -> Callable[[Callable[[T_State], None]], Callable[[], None]]: ...

    def subscribe(args: Any) -> Any:
        """Subscribe to state changes."""

else:

    def subscribe(
        args: tuple[StatePath, ...],
    ) -> Callable[[Callable[[tuple[StatePath, ...]], None]], Callable[[], None]]:
        def register_callback(
            callback: Callable[[tuple[StatePath, ...]], None],
        ) -> Callable[[], None]:
            callback(tuple(get_state(arg) for arg in args))
            for arg in args:
                slice_name = arg.slice_name
                state_name = arg.state
                if slice_name not in SUBSCRIPTIONS:
                    SUBSCRIPTIONS[slice_name] = {}
                if state_name not in SUBSCRIPTIONS[slice_name]:
                    SUBSCRIPTIONS[slice_name][state_name] = []
                SUBSCRIPTIONS[slice_name][state_name].append((callback, args))

            def unsubscribe() -> None:
                for arg in args:
                    slice_name = arg.slice_name
                    state_name = arg.state
                    if slice_name in SUBSCRIPTIONS and state_name in SUBSCRIPTIONS[slice_name]:
                        SUBSCRIPTIONS[slice_name][state_name].remove((callback, args))
                        if not SUBSCRIPTIONS[slice_name][state_name]:
                            del SUBSCRIPTIONS[slice_name][state_name]
                            if not SUBSCRIPTIONS[slice_name]:
                                del SUBSCRIPTIONS[slice_name]

            return unsubscribe

        return register_callback


def register_extra_reducer(
    state: StatePath,
    callback: Callable[[T_Slice], T_Slice],
) -> None:
    slice_name = state.slice_name
    state_name = state.state
    if slice_name not in SUBSCRIPTIONS:
        SUBSCRIPTIONS[slice_name] = {}
    if state_name not in SUBSCRIPTIONS[slice_name]:
        SUBSCRIPTIONS[slice_name][state_name] = []
    SUBSCRIPTIONS[slice_name][state_name].append((lambda _: dispatch(callback), []))


def register_extra_reducer_with_state(
    state: StatePath,
    callback: Callable[[T_Slice, Any], T_Slice],
) -> None:
    slice_name = state.slice_name
    state_name = state.state
    if slice_name not in SUBSCRIPTIONS:
        SUBSCRIPTIONS[slice_name] = {}
    if state_name not in SUBSCRIPTIONS[slice_name]:
        SUBSCRIPTIONS[slice_name][state_name] = []

    SUBSCRIPTIONS[slice_name][state_name].append(
        (lambda args: dispatch(callback, args[0]), [state])
    )
