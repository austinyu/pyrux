"""Redux-like store implementation for managing state in Python applications."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import (
    Any,
    NamedTuple,
    TypeVar,
    TypeVarTuple,
    cast,
    dataclass_transform,
    overload,
)

from pydantic import BaseModel, ConfigDict

from .slice import Slice, StatePath

__all__ = [
    "Store",
    "create_store",
    "get_store",
    "get_state",
    "get_slice",
    "dispatch",
    "dispatch_state",
    "dispatch_slice",
    "subscribe",
    "force_notify",
]


@dataclass_transform(kw_only_default=True)
class Store(BaseModel):
    """Redux store class."""

    model_config = ConfigDict(frozen=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)


STORE_CLS: type[Store] | None = None
STORE: dict[str, Slice] | None = None

AnyStore = TypeVar("AnyStore", bound=Store)
AnySlice = TypeVar("AnySlice", bound=Slice)
AnyState = TypeVar("AnyState")
ArgT = TypeVarTuple("ArgT")


class _ExtraReducerCacheKey(NamedTuple):
    subscriber_slice_name: str
    notifier_slice_name: str
    notifier_state_name: str


_EXTRA_REDUCER_CACHE: defaultdict[_ExtraReducerCacheKey, list[SubscriptionEntry]] = (
    defaultdict(list)
)
SubscriptionEntry = tuple[Callable[..., None], list[StatePath]]
SUBSCRIPTIONS: defaultdict[str, defaultdict[str, list[SubscriptionEntry]]] = defaultdict(
    lambda: defaultdict(list)
)
SLICE_TREE: dict[str, str] = {}
SLICE_NAME_CACHE: dict[str, str] = {}


def _get_slice_name_fm_reducer(reducer: Callable) -> str:
    return reducer.__qualname__.split(".")[0]


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


def _clear_store() -> None:
    global STORE, STORE_CLS  # pylint: disable=W0603
    for (
        subscriber,
        slice_name,
        state_name,
    ), extra_reducers in _EXTRA_REDUCER_CACHE.items():
        if slice_name in SLICE_TREE and subscriber in SLICE_TREE:
            root_slice_name = SLICE_TREE[slice_name]
            SUBSCRIPTIONS[root_slice_name][state_name] = [
                reducer
                for reducer in SUBSCRIPTIONS[root_slice_name][state_name]
                if reducer not in extra_reducers
            ]
    STORE = None
    STORE_CLS = None
    SLICE_NAME_CACHE.clear()
    SLICE_TREE.clear()


def create_store(store: Store, recreate: bool = False) -> None:
    """Create a store with the given slices.

    Args:
        - store: The store to create. Must be a subclass of `Store`.
        - recreate: If True, recreate the store even if it already exists.
            This will clear the existing store and create a new one.
    """
    global STORE_CLS, STORE, SLICE_NAME_CACHE  # pylint: disable=W0603
    if recreate:
        _clear_store()

    if STORE_CLS is not None:
        raise RuntimeError("Store already initialized")
    if not isinstance(store, Store):
        raise TypeError(f"Expected a Store, got {type(store)}")
    STORE_CLS = store.__class__
    STORE = {
        getattr(store, name).slice_name: getattr(store, name)
        for name in type(store).model_fields.keys()
    }
    SLICE_NAME_CACHE = {
        getattr(store, name).slice_name: name for name in type(store).model_fields.keys()
    }

    for one_slice in STORE.values():
        if not isinstance(one_slice, Slice):
            raise TypeError(f"Expected a Slice, got {type(one_slice)}")
        slice_name = one_slice.__class__.__name__
        _register_bases(one_slice.__class__, slice_name)

    # map args in extra_reducers to the root slice name
    for key, extra_reducers in _EXTRA_REDUCER_CACHE.items():
        try:
            extra_reducers = [
                (
                    reducer,
                    [
                        StatePath(_get_root_slice_name(arg.slice_name), arg.state)
                        for arg in args
                    ],
                )
                for reducer, args in extra_reducers
            ]
            _EXTRA_REDUCER_CACHE[key] = extra_reducers
        except KeyError:
            pass  # the slice that declares an extra reducer is not in the store

    # register extra reducers
    for (
        subscriber,
        slice_name,
        state_name,
    ), extra_reducers in _EXTRA_REDUCER_CACHE.items():
        if subscriber not in SLICE_TREE:
            # the slice that declares an extra reducer is not in the store
            continue
        if slice_name not in SLICE_TREE:
            # no slice in the store inherit from the slice that declares the extra reducer
            continue
        root_slice_name = SLICE_TREE[slice_name]
        SUBSCRIPTIONS[root_slice_name][state_name].extend(extra_reducers)

    for one_slice in STORE.values():
        _dispatch(one_slice.slice_name, one_slice, force=True)


@overload
def get_store(store_type: type[AnyStore]) -> AnyStore: ...


@overload
def get_store(store_type: None = None) -> Store: ...


def get_store(store_type=None):
    """Get the store."""
    if STORE_CLS is None or STORE is None:
        raise RuntimeError("Store not initialized")
    if store_type is not None and not issubclass(store_type, STORE_CLS):
        raise TypeError(f"Expected a {STORE_CLS}, got {store_type}")
    return STORE_CLS.model_validate(
        {SLICE_NAME_CACHE[name]: one_slice for name, one_slice in STORE.items()}
    )  # type: ignore[return-value]


def _get_root_slice_name(slice_name: str) -> str:
    """Get the root slice name."""
    if slice_name not in SLICE_TREE:
        raise KeyError(
            f"Slice '{slice_name}' not found in store. "
            + f"Slices in the store: {list(SLICE_TREE.keys())}"
        )
    root_slice_name = SLICE_TREE[slice_name]
    if STORE is not None and root_slice_name not in STORE:
        raise KeyError(f"Slice '{root_slice_name}' not found in store")
    return root_slice_name


def get_slice(slice_type: type[Slice]) -> Slice:
    """Get the slice by name."""
    return _get_slice_from_name(cast(str, slice_type.slice_name))


def _check_store_init() -> None:
    """Check if the store is initialized."""
    if STORE is None:
        raise RuntimeError("Store not initialized")


def _get_slice_from_name(slice_name: str) -> Slice:
    """Get the slice by name."""
    _check_store_init()
    assert STORE is not None, "Store not initialized"
    root_slice_name = _get_root_slice_name(slice_name)
    if root_slice_name not in STORE:
        raise KeyError(f"Slice '{root_slice_name}' not found in store")
    return STORE[root_slice_name]


@overload
def get_state(path: StatePath) -> Any: ...


@overload
def get_state(path: AnyState) -> AnyState: ...


def get_state(path) -> Any:
    """Get the value of a state in the store.

    Args:
        - path: The state to get. Can be represented as `SliceName.state_name` or
            `redux.build_path("SliceName", "state_name")`.

    Returns:
        - The value of the state.
    """
    _check_store_init()
    assert STORE is not None, "Store not initialized"
    if not isinstance(path, StatePath):
        raise TypeError(f"Expected a StatePath, got {type(path)}")
    root_slice_name = _get_root_slice_name(path.slice_name)
    state_name = path.state
    if root_slice_name not in STORE:
        raise KeyError(f"Slice '{path.slice_name}' not found in store")
    if state_name not in STORE[root_slice_name].model_fields_set:
        raise KeyError(f"State '{state_name}' not found in slice '{path.slice_name}'")
    return STORE[root_slice_name].get_state(state_name)


Reducer = Callable[[Slice], Slice]
ReducerWithPayload = Callable[[Slice, AnyState], Slice]


def _dispatch(slice_name: str, new_slice: Slice, force: bool = False) -> None:
    _check_store_init()
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


def dispatch_slice(new_slice: Slice) -> None:
    """Dispatch a new slice to the store."""
    if not isinstance(new_slice, Slice):
        raise TypeError(f"Expected a Slice, got {type(new_slice)}")
    _dispatch(new_slice.slice_name, new_slice)


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
    """Dispatch a reducer function to change the state of the store.

    Args:
        reducer: A function that takes a slice and optionally a payload, and
            returns a new slice.
        payload: The new value for the state. The data type of payload must match the type
            annotation of the state in the slice.

    ```python
    from __future__ import annotations
    import redux as rd

    class CameraSlice(rd.Slice):
        exposure: float = 0.0
        gain: float = 0.0

        # reducer can take in a payload
        @rd.reduce
        def set_exposure_s(piece: CameraSlice, exposure: float) -> CameraSlice:
            return piece.update([(CameraSlice.exposure, exposure)])

        # reducer can take no payload
        @rd.reduce
        def reset_exposure_s(piece: CameraSlice) -> CameraSlice:
            return piece.update([(CameraSlice.exposure, 0.0)])

    class Store(rd.Store):
        camera: CameraSlice

    rd.create_store(Store(camera=CameraSlice(exposure=0.1, gain=0.2)))

    rd.dispatch(CameraSlice.set_exposure_s, 0.5)
    assert rd.get_state(CameraSlice.exposure) == 0.5

    rd.dispatch(CameraSlice.reset_exposure_s)
    assert rd.get_state(CameraSlice.exposure) == 0.0
    ```
    """
    if not callable(reducer):
        raise TypeError(f"Expected a callable, got {type(reducer)}")
    root_slice_name: str = _get_root_slice_name(_get_slice_name_fm_reducer(reducer))
    assert STORE is not None, "Store not initialized"
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


def force_notify(states: Sequence[StatePath | Any]) -> None:
    """Notify subscribers of state value even if the state did not change."""
    _check_store_init()
    assert STORE is not None, "Store not initialized"
    for state in states:
        root_slice_name = _get_root_slice_name(state.slice_name)
        state_name = state.state
        if root_slice_name in STORE and state_name in STORE[root_slice_name].model_fields_set:
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
    """Dispatch a state change to the store.

    Args:
        state: The state to change. Can be represented as `SliceName.state_name` or
            `redux.build_path("SliceName", "state_name")`.
        payload: The new value for the state. The data type of payload must match the type
            annotation of the state in the slice.

    Returns:
        None

    Raises:
        RuntimeError: If the store is not initialized.
        Exception: If the dispatch fails, the store will be reverted to its previous state.

    Example:

    ```python
    import redux as rd

    class CameraSlice(rd.Slice):
        exposure: float = 0.0
        gain: float = 0.0

    class Store(rd.Store):
        camera: CameraSlice

    rd.create_store(Store(camera=CameraSlice(exposure=0.1, gain=0.2)))

    assert rd.get_state(CameraSlice.exposure) == 0.1
    assert rd.get_state(CameraSlice.gain) == 0.2

    rd.dispatch_state(CameraSlice.exposure, 100)
    assert rd.get_state(CameraSlice.exposure) == 100

    rd.dispatch_state(rd.build_path("CameraSlice", "gain"), 200)
    assert rd.get_state(CameraSlice.gain) == 200
    ```
    """
    _check_store_init()
    assert STORE is not None, "Store not initialized"
    root_slice_name = _get_root_slice_name(state.slice_name)
    old_slice = STORE[root_slice_name]
    try:
        new_slice = STORE[root_slice_name].update([(state, payload)])
        _dispatch(root_slice_name, new_slice)
    except Exception as e:
        _dispatch(root_slice_name, old_slice, force=True)
        raise e


@overload
def subscribe(
    *args: StatePath,
) -> Callable[[Callable[..., None]], Callable[[], None]]: ...


@overload
def subscribe(
    *args: *ArgT,
) -> Callable[[Callable[[*ArgT], None]], Callable[[], None]]: ...


def subscribe(*args):
    """Subscribe to state changes.

    Args:
        *args: Any number of states can be represented as `SliceName.state_name` or
            `redux.build_path("SliceName", "state_name")`.

    Returns:
        A decorator that takes a callback function and returns a function to unsubscribe.

    Example:

    ```python
    import redux as rd

    class CameraSlice(rd.Slice):
        exposure: float = 0.0
        gain: float = 0.0

    class Store(rd.Store):
        camera: CameraSlice

    rd.create_store(Store(camera=CameraSlice(exposure=0.1, gain=0.2)))

    @rd.subscribe(CameraSlice.exposure, CameraSlice.gain)
    def print_exposure_change(
        exposure: float,
        gain: float,
    ) -> None:
        print(f"Exposure changed: {exposure}, {gain}")

    def careless_subscribe(exposure: float) -> None:
        print(f"Exposure changed: {exposure}")

    unsubscribe = rd.subscribe(CameraSlice.exposure)(careless_subscribe)
    unsubscribe()  # Unsubscribe from the callback

    # Output:
    # Exposure changed: 0.1, 0.2
    # Exposure changed: 0.1
    ```
    """
    root_args = [StatePath(_get_root_slice_name(path.slice_name), path.state) for path in args]

    def register_callback(callback: Callable[..., None], /) -> Callable[[], None]:
        callback(*tuple(get_state(arg) for arg in args))
        for arg in root_args:
            SUBSCRIPTIONS[arg.slice_name][arg.state].append((callback, root_args))

        def unsubscribe() -> None:
            for arg in root_args:
                SUBSCRIPTIONS[arg.slice_name][arg.state].remove((callback, root_args))

        return unsubscribe

    return register_callback


@overload
def reduce(
    reducer: Callable[[AnySlice, AnyState], AnySlice],
) -> staticmethod[[AnySlice, AnyState], AnySlice]: ...


@overload
def reduce(reducer: Callable[[AnySlice], AnySlice]) -> staticmethod[[AnySlice], AnySlice]: ...


def reduce(reducer):
    """Decorator to register a reducer function for a slice.

    Args:
        reducer: A function that takes a slice and optionally a payload, and
            returns a new slice.

    Example:

    ```python
    from __future__ import annotations
    import redux as rd

    class CameraSlice(rd.Slice):
        exposure: float = 0.0
        gain: float = 0.0

        # reducer can take in a payload
        @rd.reduce
        def set_exposure_s(piece: CameraSlice, exposure: float) -> CameraSlice:
            return piece.update([(CameraSlice.exposure, exposure)])

        # reducer can take no payload
        @rd.reduce
        def reset_exposure_s(piece: CameraSlice) -> CameraSlice:
            return piece.update([(CameraSlice.exposure, 0.0)])
    ```
    """
    return staticmethod(reducer)


ReducerNoArgs = Callable[[AnySlice], AnySlice]
ReducerWithArgs = Callable[[AnySlice, *ArgT], AnySlice]
StaticReducerNoArgs = staticmethod  # [[AnySlice], AnySlice]
# staticmethod[[AnySlice, *ArgT], AnySlice] is not supported yet
StaticReducerWithArgs = staticmethod  # [..., AnySlice]


def extra_reduce(
    *args: *ArgT,
) -> Callable[
    [ReducerNoArgs[AnySlice] | ReducerWithArgs[AnySlice, *ArgT]],
    StaticReducerNoArgs | StaticReducerWithArgs,
]:
    """Decorator to register an extra reducer function for a slice."""

    @overload
    def wrap_reducer(reducer: ReducerWithArgs[AnySlice, *ArgT]) -> StaticReducerWithArgs: ...

    @overload
    def wrap_reducer(reducer: ReducerNoArgs[AnySlice]) -> StaticReducerNoArgs: ...

    def wrap_reducer(reducer, _args=args) -> staticmethod:
        args_count: int = reducer.__code__.co_argcount
        if args_count == 0:
            raise ValueError("Reducer function must accept at least one argument (slice).")

        subscriber_slice_name: str = _get_slice_name_fm_reducer(reducer)
        for notifier_state in args:
            assert isinstance(notifier_state, StatePath)
            notifier_slice_name = notifier_state.slice_name
            notifier_state_name = notifier_state.state

            def reducer_in_dispatch_with_args(
                *states: *ArgT,
                _reducer: Callable[[Slice, *ArgT], Slice] = reducer,
                _subscriber_slice_name: str = subscriber_slice_name,
            ) -> None:
                _dispatch(
                    _subscriber_slice_name,
                    _reducer(_get_slice_from_name(_subscriber_slice_name), *states),
                )

            def reducer_in_dispatch_no_args(
                *_: *ArgT,
                _reducer: Callable[[Slice], Slice] = reducer,
                _subscriber_slice_name: str = subscriber_slice_name,
            ) -> None:
                _dispatch(
                    _subscriber_slice_name,
                    _reducer(_get_slice_from_name(_subscriber_slice_name)),
                )

            if args_count >= 2:
                entry: SubscriptionEntry = (
                    reducer_in_dispatch_with_args,
                    cast(list[StatePath], list(args)),
                )
            else:
                assert args_count == 1
                entry = (reducer_in_dispatch_no_args, cast(list[StatePath], list(args)))
            _EXTRA_REDUCER_CACHE[
                _ExtraReducerCacheKey(
                    subscriber_slice_name, notifier_slice_name, notifier_state_name
                )
            ].append(entry)

        return staticmethod(reducer)

    return wrap_reducer  # type: ignore[return-value]
