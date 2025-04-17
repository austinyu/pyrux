from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVarTuple, Any, cast, overload, TypeVar
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
    "force_notify",
    "dispatch_state",
]

STORE: dict[str, Slice] | None = None

Ts = TypeVarTuple("Ts")
Ts_INTERNAL = TypeVarTuple("Ts_INTERNAL")
AnySlice = TypeVar("AnySlice", bound=Slice)
AnyState = TypeVar("AnyState", invaria)

SubscriptionEntry = tuple[Callable[..., None], list[StatePath]]
SUBSCRIPTIONS: dict[str, dict[str, list[SubscriptionEntry]]] = {}


class _StoreDataModel:
    pass


def _get_slice_name(reducer: Callable) -> str:
    return reducer.__qualname__.split(".")[0]


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
    _StoreDataModel.__annotations__ = {name: slice.__class__ for name, slice in STORE.items()}


def dump_store() -> dict[str, Any]:
    """Dump the store to a dictionary."""
    assert STORE is not None, "Store not initialized"
    return {
        slice_name: slice_content.model_dump() for slice_name, slice_content in STORE.items()
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


def get_store_data_model() -> type[_StoreDataModel]:
    """Get the store data model. The returned class is a class based data model.
    Class based data model defines the attributes as name and its type hints. Examples include
    `TypedDict`, `dataclass`, `pydantic.BaseModel`, etc. This function is useful for other
    packages to serialize or deserialize the store data model.
    Here is an example:

    ```python
    class StoreDataModel:
        CameraSlice: CameraSlice
        Snapshot: Snapshot
    ```
    """
    assert STORE is not None, "Store not initialized"
    return _StoreDataModel


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


Reducer = Callable[[Slice], Slice]
ReducerWithPayload = Callable[[Slice, AnyState], Slice]


def _dispatch(slice_name: str, new_slice: Slice) -> None:
    assert STORE is not None, "Store not initialized"
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
                    *tuple(
                        get_state(path) if path.state != state_name else new_state
                        for path in paths
                    )
                )

    STORE[slice_name] = new_slice


if TYPE_CHECKING:
    # For callables that take only one argument (no payload)
    @overload
    def dispatch(
        reducer: Callable[[AnySlice], AnySlice],
        payload: None = None,
    ) -> None: ...

    # For callables that take two arguments (with payload)
    @overload
    def dispatch(
        reducer: Callable[[AnySlice, AnyState], AnySlice],
        payload: AnyState,
    ) -> None: ...

    def dispatch(
        reducer: Any,
        payload: Any = None,
    ) -> None:
        """ "Dispatch an action to the store."""

    def force_notify(states: Sequence[AnyState]) -> None:  # pylint: disable=W613
        """Notify subscribers of state value even if the state did not change."""

    # I could not find a way to enforce type consistency for 2 arguments in the function.
    def dispatch_state(
        state: AnyState, payload: AnyState
    ) -> None:
        """Convenient function to directly dispatch a state change."""

else:
    Reducer = Callable[[Slice], Slice] | Callable[[Slice, AnyState], Slice]

    def dispatch(reducer: Reducer, payload: Any | None = None) -> None:
        slice_name: str = _get_slice_name(reducer)
        if payload is None:
            new_slice = cast(Reducer, reducer)(STORE[slice_name])
        else:
            new_slice = cast(ReducerWithPayload, reducer)(STORE[slice_name], payload)
        _dispatch(slice_name, new_slice)

    def dispatch_state(
        state: StatePath,
        payload: AnyState,
    ) -> None:
        assert STORE is not None, "Store not initialized"
        new_slice = STORE[state.slice_name].update([(state, payload)])
        _dispatch(state.slice_name, new_slice)

    def force_notify(states: Sequence[AnyState]) -> None:
        assert STORE is not None, "Store not initialized"
        for state in states:
            slice_name = state.slice_name
            state_name = state.state
            if slice_name in STORE and state_name in STORE[slice_name].model_fields_set:
                new_state = STORE[slice_name].get_state(state_name)
                if (
                    slice_name in SUBSCRIPTIONS  # has subscribers for this slice
                    and state_name
                    in SUBSCRIPTIONS[slice_name]  # has subscribers for this state
                ):
                    for callback, paths in SUBSCRIPTIONS[slice_name][state_name]:
                        callback(
                            *tuple(
                                get_state(path) if path.state != state_name else new_state
                                for path in paths
                            )
                        )

AnyState1 = TypeVar("AnyState1")
AnyState2 = TypeVar("AnyState2")
AnyState3 = TypeVar("AnyState3")
AnyState4 = TypeVar("AnyState4")
AnyState5 = TypeVar("AnyState5")

if TYPE_CHECKING:

    @overload
    def subscribe(
        arg1: AnyState,
    ) -> Callable[[Callable[[AnyState], None]], Callable[[], None]]: ...

    @overload
    def subscribe(
        arg1: AnyState1,
        arg2: AnyState2,
    ) -> Callable[[Callable[[AnyState1, AnyState2], None]], Callable[[], None]]: ...

    @overload
    def subscribe(
        arg1: AnyState1,
        arg2: AnyState2,
        arg3: AnyState3,
    ) -> Callable[[Callable[[AnyState1, AnyState2, AnyState3], None]], Callable[[], None]]: ...

    @overload
    def subscribe(
        arg1: AnyState1,
        arg2: AnyState2,
        arg3: AnyState3,
        arg4: AnyState4,
    ) -> Callable[
        [Callable[[AnyState1, AnyState2, AnyState3, AnyState4], None]], Callable[[], None]
    ]: ...

    @overload
    def subscribe(
        arg1: AnyState1,
        arg2: AnyState2,
        arg3: AnyState3,
        arg4: AnyState4,
        arg5: AnyState5,
    ) -> Callable[
        [Callable[[AnyState1, AnyState2, AnyState3, AnyState4, AnyState5], None]],
        Callable[[], None],
    ]: ...

    def subscribe(arg1, arg2=None, arg3=None, arg4=None, arg5=None) -> Any:
        """Subscribe to state changes."""
        raise NotImplementedError("This function is not implemented in TYPE_CHECKING mode.")

else:

    def subscribe(
        *args: StatePath,
    ) -> Callable[[Callable[..., None]], Callable[[], None]]:
        def register_callback(callback: Callable[..., None]) -> Callable[[], None]:
            callback(*tuple(get_state(arg) for arg in args))
            for arg in args:
                slice_name = arg.slice_name
                state_name = arg.state
                if slice_name not in SUBSCRIPTIONS:
                    SUBSCRIPTIONS[slice_name] = {}
                if state_name not in SUBSCRIPTIONS[slice_name]:
                    SUBSCRIPTIONS[slice_name][state_name] = []
                SUBSCRIPTIONS[slice_name][state_name].append((callback, list(args)))

            def unsubscribe() -> None:
                for arg in args:
                    slice_name = arg.slice_name
                    state_name = arg.state
                    if slice_name in SUBSCRIPTIONS and state_name in SUBSCRIPTIONS[slice_name]:
                        SUBSCRIPTIONS[slice_name][state_name].remove((callback, list(args)))
                        if not SUBSCRIPTIONS[slice_name][state_name]:
                            del SUBSCRIPTIONS[slice_name][state_name]
                            if not SUBSCRIPTIONS[slice_name]:
                                del SUBSCRIPTIONS[slice_name]

            return unsubscribe

        return register_callback


ExtraReducer = Callable[[AnySlice], AnySlice]


def register_extra_reducer(
    state: StatePath,
    callback: ExtraReducer,
) -> None:
    slice_name = state.slice_name
    state_name = state.state
    if slice_name not in SUBSCRIPTIONS:
        SUBSCRIPTIONS[slice_name] = {}
    if state_name not in SUBSCRIPTIONS[slice_name]:
        SUBSCRIPTIONS[slice_name][state_name] = []
    SUBSCRIPTIONS[slice_name][state_name].append((lambda _: dispatch(callback), []))


class ExtraReducerStates(Protocol):
    def __call__(self, slice_obj: AnySlice, *args: Any) -> AnySlice: ...


def register_extra_reducer_with_states(
    states: Sequence[StatePath],
    reducer: ExtraReducerStates,
) -> None:
    def wrapped_reducer(slice_obj: AnySlice, payload: tuple) -> AnySlice:
        return reducer(slice_obj, *payload)

    for state in states:
        slice_name = state.slice_name
        state_name = state.state
        if slice_name not in SUBSCRIPTIONS:
            SUBSCRIPTIONS[slice_name] = {}
        if state_name not in SUBSCRIPTIONS[slice_name]:
            SUBSCRIPTIONS[slice_name][state_name] = []

        SUBSCRIPTIONS[slice_name][state_name].append(
            (
                lambda *args: _dispatch(_get_slice_name(reducer), wrapped_reducer, args),
                list(states),
            )
        )
