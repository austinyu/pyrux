from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Any,
    NamedTuple,
    TypeVar,
    dataclass_transform,
    overload,
)
from collections.abc import Callable
from pydantic import BaseModel, ConfigDict


class StatePath(NamedTuple):
    slice_name: str
    state: str


@dataclass_transform(kw_only_default=True)
class Slice(BaseModel):
    model_config = ConfigDict(frozen=True)

    def __init_subclass__(cls, **_):
        def get_attr_as_internal(cls, attr_name: str) -> StatePath:
            if attr_name == "name":
                return cls.__name__
            if attr_name in {"__annotations__"}:
                return super(type(cls), cls).__getattribute__(attr_name)  # type: ignore
            if attr_name in cls.__annotations__.keys():
                return StatePath(
                    slice_name=cls.__name__,
                    state=attr_name,
                )
            return super(type(cls), cls).__getattribute__(attr_name)  # type: ignore

        cls.__class__.__getattribute__ = get_attr_as_internal

    def get_state(self, key: str) -> Any:
        if key not in self.model_fields_set:
            raise KeyError(f"State '{key}' not found in slice '{self.__class__.__name__}'")
        return self.__getattribute__(key)

    if TYPE_CHECKING:

        @property
        def name(self) -> str: ...

    if not TYPE_CHECKING:

        def __getattribute__(self, attr_name: str) -> Any:
            if attr_name == "name":
                return self.__class__.__name__
            return super().__getattribute__(attr_name)


T_Slice = TypeVar("T_Slice", bound=Slice)
T_State = TypeVar("T_State")


def immer(piece: T_Slice, update_states: dict[StatePath | Any, T_State]) -> T_Slice:
    update_dict: dict[str, T_State] = {}
    for update_path, new_state in update_states.items():
        update_dict[update_path.state] = new_state
    return piece.model_copy(update=update_dict)


@overload
def reduce(reducer: Callable[[T_Slice, Any], T_Slice]): ...


@overload
def reduce(reducer: Callable[[T_Slice], T_Slice]): ...


def reduce(reducer):
    return staticmethod(reducer)


if TYPE_CHECKING:

    def extra_reduce(
        state: T_State,
    ) -> Callable[[Callable[[T_Slice], T_Slice] | Callable[[T_Slice, T_State], T_Slice]], Any]:
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
            with_state_arg = reducer.__code__.co_argcount == 2
            return staticmethod(reducer)

        return wrap_reducer
