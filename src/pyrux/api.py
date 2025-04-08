
from __future__ import annotations
from collections.abc import Callable
from typing import Generic, Protocol, TypeVar, Any

class Slice(Protocol, Generic[SliceState, RootState]):
    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def reducer(self) -> Reducer:
        raise NotImplementedError

    @property
    def actions(self) -> dict[str, ActionCreator]:
        raise NotImplementedError

    @property
    def case_reducers(self) -> dict[str, Reducer]:
        raise NotImplementedError

    def getInitialState(self) -> SliceState:
        raise NotImplementedError

    @property
    def reducer_path(self) -> str:
        raise NotImplementedError

    @property
    def select_slice(self) -> Selector[RootState]:
        raise NotImplementedError

    @property
    def selectors(self) -> dict[str, Selector[SliceState]]:
        raise NotImplementedError

    def get_selectors(
        self, root_selector: Callable[[RootState], SliceState]
    ) -> dict[str, Selector[SliceState]]:
        raise NotImplementedError

    # injectInto: (injectable: Injectable, config?: InjectConfig & { reducerPath?: string }) => InjectedSlice
