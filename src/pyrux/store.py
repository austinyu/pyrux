from typing import TYPE_CHECKING, TypeVarTuple, Any, overload, TypeVar
from collections.abc import Sequence, Callable
from pyrux.py_api import Slice, StatePath


__all__ = [
    "create_store",
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


def create_store(slices: Sequence[Slice]) -> None:
    global STORE
    assert STORE is None, "Store already initialized"
    STORE = {slice.__class__.__name__: slice for slice in slices}


def get_store() -> dict[str, Slice]:
    assert STORE is not None, "Store not initialized"
    return STORE


def get_state(path: StatePath) -> Any:
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
    ) -> Any: ...

    # For callables that take two arguments (with payload)
    @overload
    def dispatch(
        action_creator: Callable[[T_Slice, T_State], T_Slice],
        payload: T_State,
    ) -> Any: ...

    def dispatch(
        action_creator: Any,
        payload: Any = None,
    ) -> Any: ...

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

    def subscribe(args: Any) -> Any: ...

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
    callback: Callable[[T_Slice], T_State],
) -> None:
    slice_name = state.slice_name
    state_name = state.state
    if slice_name not in SUBSCRIPTIONS:
        SUBSCRIPTIONS[slice_name] = {}
    if state_name not in SUBSCRIPTIONS[slice_name]:
        SUBSCRIPTIONS[slice_name][state_name] = []
    SUBSCRIPTIONS[slice_name][state_name].append(
        (lambda _state: dispatch(callback), []))


def register_extra_reducer_with_state(
    state: StatePath,
    callback: Callable[[T_Slice, Any], T_Slice] | Callable[[T_Slice, T_State]],
) -> None:
    slice_name = state.slice_name
    state_name = state.state
    if slice_name not in SUBSCRIPTIONS:
        SUBSCRIPTIONS[slice_name] = {}
    if state_name not in SUBSCRIPTIONS[slice_name]:
        SUBSCRIPTIONS[slice_name][state_name] = []
    with_state_arg = callback.__code__.co_argcount == 2
    if with_state_arg:
        SUBSCRIPTIONS[slice_name][state_name].append(
            (lambda _state: dispatch(callback, _state), [state]))
    else:
        SUBSCRIPTIONS[slice_name][state_name].append(
            (lambda _state: dispatch(callback), []))

