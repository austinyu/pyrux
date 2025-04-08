from __future__ import annotations

from collections.abc import Callable
from typing import Generic, Any, Protocol

from pyrux.internal_typing import (
    ActionType,
    Reducer,
    SliceState,
    RootState,
    StoreState,
    UnKnown,
    Selector,
    InternalSelector,
    InternalActionCreator,
    ReducerAndPrepare,
)
from pyrux.utils import join_path, join_action


CreateSliceReducers = dict[str, Reducer | ReducerAndPrepare]

class ActionReducerMapBuilder(Protocol):
    def add_case(
        self, action_creator: InternalActionCreator, reducer: Reducer
    ) -> None:
        raise NotImplementedError

    def add_matcher(
        self, matcher: Callable[[ActionType], bool], reducer: Reducer
    ) -> None:
        raise NotImplementedError

    def add_default_case(self, reducer: Reducer) -> None:
        raise NotImplementedError


def create_slice(
    name: str,
    initial_state: SliceState,
    reducers: CreateSliceReducers,
    extra_reducers: Callable[[ActionReducerMapBuilder], None] | None = None,
    reducer_path: str | None = None,
    selectors: dict[str, Selector[SliceState]] | None = None,
) -> Slice[SliceState, Any]:
    return Slice(
        name=name,
        initial_state=initial_state,
        raw_reducers=reducers,
        extra_reducers=extra_reducers,
        reducer_path=reducer_path,
        selectors=selectors,
    )


class Slice(Generic[SliceState, RootState]):
    def __init__(
        self,
        name: str,
        initial_state: SliceState,
        raw_reducers: CreateSliceReducers,
        extra_reducers: Callable[[ActionReducerMapBuilder], None] | None = None,
        reducer_path: str | None = None,
        selectors: dict[str, Selector[SliceState]] | None = None,
    ) -> None:
        self._name: str = name
        self._state: SliceState = initial_state
        self._raw_reducers: CreateSliceReducers = raw_reducers

        self._reducer_path: str = reducer_path or name
        self._internal_selectors: dict[str, InternalSelector[SliceState]] = {
            selector_name: InternalSelector(selector, join_path(name, selector_name))
            for selector_name, selector in (selectors or {}).items()
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def reducer(self) -> Reducer:
        def reduce(state: SliceState, action: ActionType) -> SliceState:
            if action["type"] not in self._raw_reducers.keys():
                return state

            reducer = self._raw_reducers[action["type"]]

            if isinstance(reducer, dict):  # ReducerAndPrepare
                action_payload = reducer["prepare"](action["payload"])
                action["payload"] = action_payload["payload"]
                return reducer["reducer"](state, action["payload"])

            return reducer(state, action)

        return reduce

    @property
    def actions(self) -> dict[str, InternalActionCreator]:
        return {
            action_name: InternalActionCreator(
                (lambda *args: {"type": action_name, "payload": args}),
                join_action(self._name, action_name),
            )
            for action_name in self._raw_reducers.keys()
        }

    @property
    def case_reducers(self) -> dict[str, Reducer]:
        return {
            action_name: reducer if not isinstance(reducer, dict) else reducer["reducer"]
            for action_name, reducer in self._raw_reducers.items()
        }

    def getInitialState(self) -> SliceState:
        return self._state

    @property
    def reducer_path(self) -> str:
        return self._reducer_path

    def select_slice(self, root: RootState) -> RootState:
        return root[self._name]

    @property
    def selectors(self) -> dict[str, InternalSelector[SliceState]]:
        return self._internal_selectors

    def get_selectors(
        self, root_selector: Callable[[RootState], SliceState]
    ) -> dict[str, InternalSelector[SliceState]]:
        return {
            name: selector.create_root_selector(root_selector)
            for name, selector in self._internal_selectors.items()
        }


class Store(Protocol, Generic[StoreState]):
    def get_state(self) -> StoreState:
        raise NotImplementedError

    def dispatch(self, action: ActionType) -> UnKnown:
        raise NotImplementedError

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        raise NotImplementedError


def configure_store(
    reducer: Reducer | dict[str, Reducer],
    middleware: Any | None = None,
    devtools: Any | None = None,
    preloadedState: StoreState | None = None,
    enhancers: Any | None = None,
) -> Store[StoreState]:
    raise NotImplementedError
