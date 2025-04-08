from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    overload,
)
from collections.abc import Callable
from pyrux.store import register_extra_reducer, register_extra_reducer_with_state
from pyrux.slice import Slice, StatePath

__all__ = [
    "reduce",
    "extra_reduce",
]


T_Slice = TypeVar("T_Slice", bound=Slice)
T_State = TypeVar("T_State")


@overload
def reduce(reducer: Callable[[T_Slice, Any], T_Slice]): ...


@overload
def reduce(reducer: Callable[[T_Slice], T_Slice]): ...


def reduce(reducer):
    """Decorator to register a reducer function for a slice."""
    return staticmethod(reducer)


if TYPE_CHECKING:

    def extra_reduce(
        state: T_State,
    ) -> Callable[[Callable[[T_Slice], T_Slice] | Callable[[T_Slice, T_State], T_Slice]], Any]:
        """Decorator to register a foreign dependency reducer function."""
        def wrap_reducer(
            reducer: Callable[[T_Slice, Any], T_Slice] | Callable[[T_Slice, T_State], T_Slice],
        ) -> Any:
            return staticmethod(reducer)

        return wrap_reducer  # type: ignore

else:

    def extra_reduce(
        state: StatePath,
    ) -> Callable[[Callable[[T_Slice], T_Slice] | Callable[[T_Slice, T_State], T_Slice]], Any]:
        def wrap_reducer(
            reducer: Callable[[T_Slice, Any], T_Slice] | Callable[[T_Slice, T_State], T_Slice],
        ) -> Any:
            args_count: int = reducer.__code__.co_argcount
            if args_count == 1:
                register_extra_reducer(state, reducer)
            elif args_count == 2:
                register_extra_reducer_with_state(state, reducer)
            else:
                raise TypeError(
                    f"Reducer must accept either one or two arguments, got {args_count}."
                )
            return staticmethod(reducer)

        return wrap_reducer
