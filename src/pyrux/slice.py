from __future__ import annotations
from typing import TYPE_CHECKING, Any, NamedTuple, Sequence, dataclass_transform, Self, TypeVar
from pydantic import BaseModel, ConfigDict

T_State = TypeVar("T_State")

class StatePath(NamedTuple):
    """Internal representation of a state path."""
    slice_name: str
    state: str


@dataclass_transform(kw_only_default=True)
class Slice(BaseModel):
    """Slice class for managing state in a Redux-like store."""
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
        """Get the state of a specific key."""
        if key not in self.model_fields_set:
            raise KeyError(f"State '{key}' not found in slice '{self.__class__.__name__}'")
        return self.__getattribute__(key)

    if TYPE_CHECKING:
        def update(self, update_states: Sequence[tuple[T_State, T_State]]) -> Self:
            """Update the slice state with new values by creating a new instance."""
            ...

    else:
        def update(self, update_states: Sequence[tuple[StatePath, Any]]) -> Self:
            return self.model_copy(update={
                update_path.state: new_state
                for update_path, new_state in update_states
            })

    if TYPE_CHECKING:

        @property
        def slice_name(self) -> str: ...

    if not TYPE_CHECKING:

        def __getattribute__(self, attr_name: str) -> Any:
            if attr_name == "slice_name":
                return self.__class__.__name__
            return super().__getattribute__(attr_name)
