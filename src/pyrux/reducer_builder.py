
from typing import Callable
from pyrux.internal_typing import ActionType, Reducer, InternalActionCreator

__all__ = [
    "add_case",
    "add_matcher",
    "add_default_case",
]

ACTION_REACTORS: dict[str, list[Reducer]] = {}

MATCH_REACTORS: list[tuple[Callable[[ActionType], bool], Reducer]] =[]

DEFAULT_REACTORS: list[Reducer] = []

def add_case(
    action_creator: InternalActionCreator, reducer: Reducer
) -> None:
    action_type = action_creator.__redux_path__
    if action_type not in ACTION_REACTORS:
        ACTION_REACTORS[action_type] = []
    ACTION_REACTORS[action_type].append(reducer)

def add_matcher(
    matcher: Callable[[ActionType], bool], reducer: Reducer
) -> None:
    MATCH_REACTORS.append((matcher, reducer))

def add_default_case(reducer: Reducer) -> None:
    DEFAULT_REACTORS.append(reducer)
