

from enum import Enum, auto
from typing_extensions import dataclass_transform

from dataclasses import dataclass
from typing import Any, Type, TypeVar, get_type_hints, Protocol, runtime_checkable



# Step 1: Define the metaclass
class DynamicMethodMeta(type):
    def __new__(cls: Type[type], name: str, bases: tuple, dct: dict) -> Any:
        # Inspect type annotations to generate methods
        annotations = dct.get('__annotations__', {})

        def __init__(self, **kwargs: Any) -> None:
            # Initialize attributes based on annotations
            for key, value in kwargs.items():
                if key in annotations:
                    setattr(self, key, value)

        dct['__init__'] = __init__
        return super().__new__(cls, name, bases, dct)

# Step 2: Define the base class with @dataclass_transform
@dataclass_transform(kw_only_default=True)
class Base(metaclass=DynamicMethodMeta):
    pass

class ActionType(Enum):
    change_exposure = auto()
    change_gain = auto()
    change_binning = auto()
    change_readout_speed = auto()




# Step 3: Define the subclass
class CameraSlice(Base):
    exposure: float
    gain: float
    binning: int
    readout_speed: int


    def change_exposure(self, new_exposure: float) -> None:
        self.exposure = new_exposure

camera = CameraSlice(
    exposure=0.01,
    gain=1.0,
    binning=1,
    readout_speed=1,
)
print(camera.readout_speed)

from enum import Enum, auto
from typing import get_type_hints



