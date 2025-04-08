

from __future__ import annotations
from collections.abc import Callable, Mapping
from typing import Generic, TypeVar, Any, TypedDict, NotRequired, Protocol



# UnKnown = Any

# Payload = Any
# PartialPayload = Any
# ActionType = TypedDict("ActionType", {"type": str, "payload": Payload | PartialPayload | None})

# SliceState = TypeVar("SliceState", bound=Mapping)
# RootState = TypeVar("RootState", bound=Mapping)  # dict[str, SliceState | Any]
# StoreState = TypeVar("StoreState", bound=Mapping, covariant=True)
# Reducer = Callable[[SliceState, ActionType], SliceState]
# ActionCreator = Callable[..., ActionType]

# SelectedState = TypeVar("SelectedState", bound=Mapping, contravariant=True)

# Selector = Callable[[SelectedState, *Any], Any]


# class ReducerAndPrepare(TypedDict):
#     reducer: Reducer
#     prepare: Callable[[PartialPayload], Payload]

# class InternalSelector(Generic[SelectedState]):
#     def __init__(
#         self,
#         selector: Selector,
#         redux_path: str,
#     ):
#         self.__redux_path__: str = redux_path
#         self._selector: Selector = selector

#     def __call__(self, state: SelectedState, *args: Any) -> Any:
#         return self._selector(state, *args)

#     def create_root_selector(
#         self, root_selector: Callable[[RootState], SelectedState]
#     ) -> InternalSelector[RootState]:
#         def select_from_root(state: RootState, *args: Any) -> Any:
#             selected_state = root_selector(state)
#             return self._selector(selected_state, *args)

#         return InternalSelector(select_from_root, self.__redux_path__)


# class InternalActionCreator:
#     def __init__(self, action_creator: ActionCreator, redux_path: str):
#         self.__redux_path__: str = redux_path
#         self._action_creator: ActionCreator = action_creator

#     def __call__(self, *args: Any) -> ActionType:
#         return self._action_creator(*args)
