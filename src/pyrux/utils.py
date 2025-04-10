from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    overload,
)
from collections.abc import Callable
from pyrux.store import (
    register_extra_reducer,
    register_extra_reducer_with_states,
    ExtraReducer,
    ExtraReducerStates,
)
from pyrux.slice import Slice, StatePath

__all__ = [
    "reduce",
    "extra_reduce",
]


AnySlice = TypeVar("AnySlice", bound=Slice)
AnyState = TypeVar("AnyState")


@overload
def reduce(reducer: Callable[[AnySlice, Any], AnySlice]): ...


@overload
def reduce(reducer: Callable[[AnySlice], AnySlice]): ...


def reduce(reducer):
    """Decorator to register a reducer function for a slice."""
    return staticmethod(reducer)


AnyState1 = TypeVar("AnyState1")
AnyState2 = TypeVar("AnyState2")
AnyState3 = TypeVar("AnyState3")
AnyState4 = TypeVar("AnyState4")
AnyState5 = TypeVar("AnyState5")


if TYPE_CHECKING:

    @overload
    def extra_reduce(
        state1: AnyState1,
    ) -> Callable[[ExtraReducer | Callable[[AnySlice, AnyState1], AnySlice]], Any]: ...

    @overload
    def extra_reduce(
        state1: AnyState1, state2: AnyState2
    ) -> Callable[
        [
            ExtraReducer
            | Callable[[AnySlice, AnyState1], AnySlice]
            | Callable[[AnySlice, AnyState2], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2], AnySlice]
        ],
        Any,
    ]: ...

    @overload
    def extra_reduce(
        state1: AnyState1, state2: AnyState2, state3: AnyState3
    ) -> Callable[
        [
            ExtraReducer
            | Callable[[AnySlice, AnyState1], AnySlice]
            | Callable[[AnySlice, AnyState2], AnySlice]
            | Callable[[AnySlice, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState3], AnySlice]
        ],
        Any,
    ]: ...

    @overload
    def extra_reduce(
        state1: AnyState1, state2: AnyState2, state3: AnyState3, state4: AnyState4
    ) -> Callable[
        [
            ExtraReducer
            | Callable[[AnySlice, AnyState1], AnySlice]
            | Callable[[AnySlice, AnyState2], AnySlice]
            | Callable[[AnySlice, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState3, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState3, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState3, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState3, AnyState4], AnySlice]
        ],
        Any,
    ]: ...

    @overload
    def extra_reduce(
        state1: AnyState1,
        state2: AnyState2,
        state3: AnyState3,
        state4: AnyState4,
        state5: AnyState5,
    ) -> Callable[
        [
            ExtraReducer
            | Callable[[AnySlice, AnyState1], AnySlice]
            | Callable[[AnySlice, AnyState2], AnySlice]
            | Callable[[AnySlice, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState3, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState3, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState4, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState3], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState3, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState3, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState4, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState3, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState3, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState4, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState3, AnyState4, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState3, AnyState4], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState3, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState2, AnyState4, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState1, AnyState3, AnyState4, AnyState5], AnySlice]
            | Callable[[AnySlice, AnyState2, AnyState3, AnyState4, AnyState5], AnySlice]
            | Callable[
                [AnySlice, AnyState1, AnyState2, AnyState3, AnyState4, AnyState5], AnySlice
            ]
        ],
        Any,
    ]: ...

    def extra_reduce(
        state1: AnyState1, state2=None, state3=None, state4=None, state5=None
    ) -> Callable[[ExtraReducer | ExtraReducerStates], Any]:
        """Decorator to register a foreign dependency reducer function."""

        def wrap_reducer(
            reducer: Callable[[AnySlice, Any], AnySlice]
            | Callable[[AnySlice, AnyState], AnySlice],
        ) -> Any:
            return staticmethod(reducer)

        return wrap_reducer  # type: ignore

else:

    def extra_reduce(
        *states: StatePath,
    ) -> Callable[[ExtraReducer | ExtraReducerStates], Any]:
        def wrap_reducer(reducer: ExtraReducer | ExtraReducerStates) -> Any:
            args_count: int = reducer.__code__.co_argcount
            if args_count == 0:
                raise ValueError("Reducer function must accept at least one argument (slice).")
            if args_count == 1:
                register_extra_reducer(states[0], reducer)
            elif args_count >= 2:
                register_extra_reducer_with_states(states, reducer)
            return staticmethod(reducer)

        return wrap_reducer
