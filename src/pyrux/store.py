from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Literal, NamedTuple, Protocol, Any, cast, overload, TypeVar
from collections.abc import Sequence, Callable

from pydantic import BaseModel, create_model

from pyrux.slice import Slice, StatePath


__all__ = [
    "clear_store",
    "create_store",
    "dump_store",
    "get_store_pydantic_model",
    "get_store",
    "load_store",
    "get_state",
    "get_slice",
    "dispatch",
    "subscribe",
    "force_notify",
    "dispatch_state",
]

STORE: dict[str, Slice] | None = None

AnySlice = TypeVar("AnySlice", bound=Slice)
AnyState = TypeVar("AnyState")


class _ExtraReducerCacheKey(NamedTuple):
    subscriber_slice_name: str
    notifier_slice_name: str
    notifier_state_name: str


_EXTRA_REDUCER_CACHE: defaultdict[_ExtraReducerCacheKey, list[SubscriptionEntry]] = \
    defaultdict(list)
SubscriptionEntry = tuple[Callable[..., None], list[StatePath]]
SUBSCRIPTIONS: defaultdict[str, defaultdict[str, list[SubscriptionEntry]]] = defaultdict(
    lambda: defaultdict(list)
)
SLICE_TREE: dict[str, str] = {}


class _StoreDataModel:
    pass


def _get_slice_name_fm_reducer(reducer: Callable) -> str:
    return reducer.__qualname__.split(".")[0]


def clear_store() -> None:
    """Clear the store."""
    global STORE
    assert STORE is not None, "Store not initialized"
    for (subscriber, slice_name, state_name), extra_reducers in _EXTRA_REDUCER_CACHE.items():
        if subscriber in STORE:
            root_slice_name = SLICE_TREE[slice_name]
            SUBSCRIPTIONS[root_slice_name][state_name] = [
                reducer
                for reducer in SUBSCRIPTIONS[root_slice_name][state_name]
                if reducer not in extra_reducers
            ]
    STORE = None
    SLICE_TREE.clear()


def _register_bases(one_slice: type[Slice], root: str) -> None:
    """Register the base classes of the slice."""
    slice_name = one_slice.__name__
    is_leaf = len(one_slice.__bases__) == 1 and one_slice.__bases__[0] is Slice
    if is_leaf:
        SLICE_TREE[slice_name] = root
    else:
        SLICE_TREE[slice_name] = root
        for base in one_slice.__bases__:
            _register_bases(base, root)


def create_store(slices: Sequence[Slice]) -> None:
    """Create the store with the given slices."""
    global STORE
    assert STORE is None, "Store already initialized"
    STORE = {}
    _StoreDataModel.__annotations__ = {}
    for one_slice in slices:
        if not isinstance(one_slice, Slice):
            raise TypeError(f"Expected a Slice, got {type(one_slice)}")
        slice_name = one_slice.__class__.__name__
        STORE[slice_name] = one_slice
        _StoreDataModel.__annotations__[slice_name] = one_slice.__class__
        _register_bases(one_slice.__class__, slice_name)

    # map args in extra_reducers to the root slice name
    for key, extra_reducers in _EXTRA_REDUCER_CACHE.items():
        try:
            extra_reducers = [
                (
                    reducer,
                    [StatePath(_get_root_slice_name(arg.slice_name), arg.state) for arg in args],
                )
                for reducer, args in extra_reducers
            ]
            _EXTRA_REDUCER_CACHE[key] = extra_reducers
        except KeyError:
            pass  # the slice that declares an extra reducer is not in the store


    # register extra reducers
    for (subscriber, slice_name, state_name), extra_reducers in _EXTRA_REDUCER_CACHE.items():
        if subscriber not in SLICE_TREE:
            # the slice that declares an extra reducer is not in the store
            continue
        if SLICE_TREE[slice_name] not in STORE:
            # no slice in the store inherit from the slice that declares the extra reducer
            continue
        root_slice_name = SLICE_TREE[slice_name]
        SUBSCRIPTIONS[root_slice_name][state_name].extend(extra_reducers)
        force_notify([StatePath(slice_name, state_name)])

def dump_store() -> dict[str, Any]:
    """Dump the store to a dictionary."""
    assert STORE is not None, "Store not initialized"
    return {
        slice_name: slice_content.model_dump() 
        for slice_name, slice_content in STORE.items()
    }

def load_store(data: dict[str, Any]) -> None:
    """Load the store from a dictionary."""
    assert STORE is not None, "Store not initialized"

    for slice_name, slice_content in STORE.items():
        if slice_name in data:
            slice_content.model_validate(data[slice_name])
        else:
            raise KeyError(f"Slice '{slice_name}' not found in store")
    
    for slice_name, slice_content in STORE.items():
        if slice_name in data:
            STORE[slice_name] = slice_content.model_validate(data[slice_name])
        else:
            raise KeyError(f"Slice '{slice_name}' not found in store")

def get_store_pydantic_model() -> type[BaseModel]:
    """Dump the store to a pydantic model."""
    assert STORE is not None, "Store not initialized"
    sub_models: dict[str, type[BaseModel]] = {}
    for slice_name, slice_content in STORE.items():
        model_fields = slice_content.__class__.model_fields
        sub_models[slice_name] = create_model(
            slice_name,
            **{name: field.annotation for name, field in model_fields.items()},  # type: ignore
        )
    return create_model(
        "Store",
        **{
            slice_name: sub_model
            for slice_name, sub_model in sub_models.items()
        },  # type: ignore
    )
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


def _get_root_slice_name(slice_name: str) -> str:
    """Get the root slice name."""
    if slice_name not in SLICE_TREE:
        raise KeyError(f"Slice '{slice_name}' not found in store")
    root_slice_name = SLICE_TREE[slice_name]
    if STORE is not None and root_slice_name not in STORE:
        raise KeyError(f"Slice '{root_slice_name}' not found in store")
    return root_slice_name


def get_slice(slice_type: type[Slice]) -> Slice:
    """Get the slice by name."""
    return _get_slice_from_name(cast(str, slice_type.slice_name))


def _get_slice_from_name(slice_name: str) -> Slice:
    """Get the slice by name."""
    assert STORE is not None, "Store not initialized"
    root_slice_name = _get_root_slice_name(slice_name)
    if root_slice_name not in STORE:
        raise KeyError(f"Slice '{root_slice_name}' not found in store")
    return STORE[root_slice_name]


if TYPE_CHECKING:

    @overload
    def get_state(path: StatePath) -> Any: ...

    @overload
    def get_state(path: AnyState) -> AnyState: ...

    def get_state(path) -> Any:
        """Get the state of a specific slice."""

else:

    def get_state(path: StatePath) -> Any:
        """Get the state of a specific path."""
        assert STORE is not None, "Store not initialized"
        root_slice_name = _get_root_slice_name(path.slice_name)
        state_name = path.state
        if root_slice_name not in STORE:
            raise KeyError(f"Slice '{path.slice_name}' not found in store")
        if state_name not in STORE[root_slice_name].model_fields_set:
            raise KeyError(f"State '{state_name}' not found in slice '{path.slice_name}'")
        return STORE[root_slice_name].get_state(state_name)


Reducer = Callable[[Slice], Slice]
ReducerWithPayload = Callable[[Slice, AnyState], Slice]


def _dispatch(slice_name: str, new_slice: Slice, force: bool=False) -> None:
    assert STORE is not None, "Store not initialized"
    slice_state_names = new_slice.model_fields_set
    root_slice_name = _get_root_slice_name(slice_name)
    for state_name in slice_state_names:
        new_state = new_slice.get_state(state_name)
        if (
            # state changed or force
            (STORE[root_slice_name].get_state(state_name) != new_state or force)
            and slice_name in SUBSCRIPTIONS  # has subscribers for this slice
            and state_name in SUBSCRIPTIONS[root_slice_name]  # has subscribers for this state
        ):
            for callback, paths in SUBSCRIPTIONS[root_slice_name][state_name]:
                callback(
                    *tuple(
                        get_state(path) if path.state != state_name else new_state
                        for path in paths
                    )
                )

    STORE[root_slice_name] = new_slice


if TYPE_CHECKING:
    # For callables that take only one argument (no payload)
    @overload
    def dispatch(reducer: Callable[[AnySlice], AnySlice]) -> None: ...

    # For callables that take two arguments (with payload)
    @overload
    def dispatch(
        reducer: Callable[[AnySlice, AnyState], AnySlice],
        payload: AnyState,
    ) -> None: ...

    def dispatch(reducer, payload=None) -> None:
        """ "Dispatch an action to the store."""

    def force_notify(states: Sequence[Any | StatePath]) -> None:  # pylint: disable=W613
        """Notify subscribers of state value even if the state did not change."""


    @overload
    def dispatch_state(state: bool, payload: bool) -> None: ...

    @overload
    def dispatch_state(state: int, payload: int) -> None: ...


    @overload
    def dispatch_state(state: str, payload: str) -> None: ...

    @overload
    def dispatch_state(state: list[AnyState], payload: list[AnyState]) -> None: ...

    @overload
    def dispatch_state(state: set[AnyState], payload: set[AnyState]) -> None: ...

    @overload
    def dispatch_state(state: dict, payload: dict) -> None: ...

    @overload
    def dispatch_state(state: tuple, payload: tuple) -> None: ...

    @overload
    def dispatch_state(state: AnyState, payload: AnyState) -> None: ...

    def dispatch_state(state, payload) -> None:
        """Convenient function to directly dispatch a state change."""

else:
    Reducer = Callable[[Slice], Slice] | Callable[[Slice, AnyState], Slice]

    def dispatch(reducer: Reducer, payload: Any | None = None) -> None:
        if not callable(reducer):
            raise TypeError(f"Expected a callable, got {type(reducer)}")
        root_slice_name: str = _get_root_slice_name(_get_slice_name_fm_reducer(reducer))
        old_slice = STORE[root_slice_name]
        try:
            if payload is None:
                new_slice = cast(Reducer, reducer)(STORE[root_slice_name])
            else:
                new_slice = cast(ReducerWithPayload, reducer)(STORE[root_slice_name], payload)
            _dispatch(root_slice_name, new_slice)
        except Exception as e:
            _dispatch(root_slice_name, old_slice, force=True)
            raise e

    def dispatch_state(
        state: StatePath,
        payload: AnyState,
    ) -> None:
        assert STORE is not None, "Store not initialized"
        root_slice_name = _get_root_slice_name(state.slice_name)
        old_slice = STORE[root_slice_name]
        try:
            new_slice = STORE[root_slice_name].update([(state, payload)])
            _dispatch(root_slice_name, new_slice)
        except Exception as e:
            _dispatch(root_slice_name, old_slice, force=True)
            raise e

    def force_notify(states: Sequence[StatePath]) -> None:
        assert STORE is not None, "Store not initialized"
        for state in states:
            root_slice_name = _get_root_slice_name(state.slice_name)
            state_name = state.state
            if (
                root_slice_name in STORE
                and state_name in STORE[root_slice_name].model_fields_set
            ):
                new_state = STORE[root_slice_name].get_state(state_name)
                if (
                    root_slice_name in SUBSCRIPTIONS  # has subscribers for this slice
                    and state_name
                    in SUBSCRIPTIONS[root_slice_name]  # has subscribers for this state
                ):
                    for callback, paths in SUBSCRIPTIONS[root_slice_name][state_name]:
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
        arg1: AnyState | StatePath,
    ) -> Callable[[Callable[[AnyState], None]], Callable[[], None]]: ...

    @overload
    def subscribe(
        arg1: AnyState1 | StatePath,
        arg2: AnyState2 | StatePath,
    ) -> Callable[[Callable[[AnyState1, AnyState2], None]], Callable[[], None]]: ...

    @overload
    def subscribe(
        arg1: AnyState1 | StatePath,
        arg2: AnyState2 | StatePath,
        arg3: AnyState3 | StatePath,
    ) -> Callable[[Callable[[AnyState1, AnyState2, AnyState3], None]], Callable[[], None]]: ...

    @overload
    def subscribe(
        arg1: AnyState1 | StatePath,
        arg2: AnyState2 | StatePath,
        arg3: AnyState3 | StatePath,
        arg4: AnyState4 | StatePath,
    ) -> Callable[
        [Callable[[AnyState1, AnyState2, AnyState3, AnyState4], None]], Callable[[], None]
    ]: ...

    @overload
    def subscribe(
        arg1: AnyState1 | StatePath,
        arg2: AnyState2 | StatePath,
        arg3: AnyState3 | StatePath,
        arg4: AnyState4 | StatePath,
        arg5: AnyState5 | StatePath,
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
        root_args = [
            StatePath(_get_root_slice_name(path.slice_name), path.state) for path in args
        ]

        def register_callback(callback: Callable[..., None]) -> Callable[[], None]:
            callback(*tuple(get_state(arg) for arg in args))
            for arg in args:
                root_slice_name = _get_root_slice_name(arg.slice_name)
                state_name = arg.state
                SUBSCRIPTIONS[root_slice_name][state_name].append((callback, root_args))

            def unsubscribe() -> None:
                for arg in args:
                    root_slice_name = _get_root_slice_name(arg.slice_name)
                    state_name = arg.state
                    if (
                        root_slice_name in SUBSCRIPTIONS
                        and state_name in SUBSCRIPTIONS[root_slice_name]
                    ):
                        SUBSCRIPTIONS[root_slice_name][state_name].remove(
                            (callback, root_args)
                        )

            return unsubscribe

        return register_callback


ExtraReducer = Callable[[AnySlice], AnySlice]


def register_extra_reducer(
    notifier_state_path: StatePath,
    reducer: ExtraReducer,
) -> None:
    notifier_slice_name = notifier_state_path.slice_name
    notifier_state_name = notifier_state_path.state
    subscriber_slice_name = _get_slice_name_fm_reducer(reducer)
    _EXTRA_REDUCER_CACHE[
        _ExtraReducerCacheKey(
            subscriber_slice_name, notifier_slice_name, notifier_state_name
        )
    ].append((lambda: reducer(_get_slice_from_name(subscriber_slice_name)), []))


class ExtraReducerStates(Protocol):
    def __call__(self, slice_obj: AnySlice, *args: Any) -> AnySlice: ...


def register_extra_reducer_with_states(
    notifier_state_paths: list[StatePath],
    reducer: ExtraReducerStates,
) -> None:
    def wrapped_reducer(slice_obj: AnySlice, payload: tuple) -> AnySlice:
        return reducer(slice_obj, *payload)

    subscriber_slice_name: str = _get_slice_name_fm_reducer(reducer)
    for notifier_state in notifier_state_paths:
        notifier_slice_name = notifier_state.slice_name
        notifier_state_name = notifier_state.state

        entry = (
            lambda *args: _dispatch(
                subscriber_slice_name,
                wrapped_reducer(_get_slice_from_name(subscriber_slice_name), args),
            ),
            notifier_state_paths,
        )

        _EXTRA_REDUCER_CACHE[
            _ExtraReducerCacheKey(
                subscriber_slice_name, notifier_slice_name, notifier_state_name
            )
        ].append(entry)
