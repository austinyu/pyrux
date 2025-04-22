from __future__ import annotations
from typing import TYPE_CHECKING, Any, NamedTuple, Sequence, dataclass_transform, Self, TypeVar
from pydantic import BaseModel, ConfigDict
import warnings

# Suppress specific warnings from Pydantic
warnings.filterwarnings(
    "ignore",
    message=r".*shadows an attribute in parent.*",
    category=UserWarning,
    module=r"pydantic\._internal\._fields",
)

T_State = TypeVar("T_State")


class StatePath(NamedTuple):
    """Internal representation of a state path."""

    slice_name: str
    state: str


def build_path(slice_name: str, state: str) -> StatePath:
    """Build a path string from slice name and state."""
    return StatePath(slice_name, state)


_SLICE_REDUX_ANNOTATIONS: dict[tuple[str, str], set[str]] = {}


@dataclass_transform(kw_only_default=True)
class Slice(BaseModel):
    """Slice class for managing state in a Redux-like store."""

    model_config = ConfigDict(frozen=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        def rec_get_annotations(cls: type, cache: set[str]) -> set[str]:
            if len(cls.__bases__) == 1 and cls.__bases__[0].__name__ == "Slice":
                return cache
            for base in cls.__bases__:
                for base_attr in base.__annotations__.keys():
                    cache.add(base_attr)
                cache = rec_get_annotations(base, cache)
            return cache

        module_name: str = cls.__module__
        slice_name: str = cls.__name__
        if (module_name, slice_name) in _SLICE_REDUX_ANNOTATIONS:
            raise TypeError(f"Slice name '{slice_name}' already exists.")

        _SLICE_REDUX_ANNOTATIONS[(module_name, slice_name)] = rec_get_annotations(
            cls, set(cls.__annotations__.keys())
        )

        def get_attr_as_internal(cls, attr_name: str) -> StatePath | Any:
            if attr_name == "slice_name":
                return cls.__name__
            if attr_name.startswith("_"):
                return super(type(cls), cls).__getattribute__(attr_name)

            if (
                (cls.__module__, cls.__name__) in _SLICE_REDUX_ANNOTATIONS  # is a slice
                and attr_name
                in _SLICE_REDUX_ANNOTATIONS[(cls.__module__, cls.__name__)]  # is a state
            ):
                return StatePath(
                    slice_name=cls.__name__,
                    state=attr_name,
                )
            return super(type(cls), cls).__getattribute__(attr_name)

        cls.__class__.__getattribute__ = get_attr_as_internal

    @property
    def slice_name(self) -> str:
        """Return the name of the slice."""
        return self.__class__.__name__

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
            return self.model_copy(
                update={
                    update_path.state: new_state for update_path, new_state in update_states
                }
            )
