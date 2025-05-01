from __future__ import annotations

import redux as rd
from redux.store import SLICE_TREE, _register_bases


class Slice1(rd.Slice):
    state1: int = 0


class Slice2(rd.Slice):
    state2: int = 0


class Slice3(Slice1):
    state3: int = 0


class Slice4(Slice3, Slice2):
    state4: int = 0


class Slice5(rd.Slice):
    state5: int = 0


class Slice6(rd.Slice):
    state6: int = 0


class Slice7(Slice4, Slice5, Slice6):
    state7: int = 0


# print(Slice7.state7)


# region Slice

from typing import Annotated, NamedTuple

from annotated_types import Ge, Gt


class _Roi(NamedTuple):
    left: Annotated[int, Ge(0)]
    top: Annotated[int, Ge(0)]
    width: Annotated[int, Gt(0)]
    height: Annotated[int, Gt(0)]


class BaseCameraSlice(rd.Slice):
    # name of the current camera, `camera_obj.device_info.name`
    name: str
    # id of the current camera, `camera_obj.device_info.id`
    camera_id: str


class BitDepthSlice(rd.Slice):
    # bit depth of the captured image (8, 12, 14, 16)
    bit_depth: Annotated[int, Gt(0)]

    @rd.reduce
    def set_bit_depth(piece: BitDepthSlice, payload: int) -> BitDepthSlice:
        return piece.update([(BitDepthSlice.bit_depth, payload)])


class RoiSlice(rd.Slice):
    # roi (left, top, width, height)
    roi: _Roi

    @rd.reduce
    def set_roi(piece: RoiSlice, payload: tuple[int, int, int, int]) -> RoiSlice:
        # let's first check the roi is within the max roi
        left, top, width, height = payload
        max_width, max_height = 1024, 1024
        if left + width > max_width:
            raise ValueError(f"Width {width} + left {left} > max width {max_width}")
        if top + height > max_height:
            raise ValueError(f"Height {height} + top {top} > max height {max_height}")
        # we also need to adjust the roi to the step requirement
        left_s, top_s, width_s, height_s = 2, 2, 2, 2
        left = left // left_s * left_s
        top = top // top_s * top_s
        width = width // width_s * width_s
        height = height // height_s * height_s
        return piece.update([(RoiSlice.roi, _Roi(left, top, width, height))])


class ExposureSlice(rd.Slice):
    # exposure time in seconds
    exposure_in_s: Annotated[float, Gt(0)]

    @rd.reduce
    def set_exposure(piece: ExposureSlice, payload: float) -> ExposureSlice:
        return piece.update([(ExposureSlice.exposure_in_s, min(100, max(0, payload)))])


class CameraSlice(BaseCameraSlice, BitDepthSlice, RoiSlice, ExposureSlice):
    owner: str

    @staticmethod
    def get_default_slice() -> CameraSlice:
        return CameraSlice(
            name="Camera",
            camera_id="camera_1",
            roi=_Roi(left=0, top=0, width=100, height=100),
            exposure_in_s=1.0,
            bit_depth=16,
            owner="owner_1",
        )


class ImgConfigSlice(rd.Slice):
    x: float
    y: float
    rotation: float
    left_right_flip: bool
    top_bottom_flip: bool
    log_display: bool
    black_level: float
    white_level: float
    low_enabled: bool
    low_threshold: float
    high_enabled: bool
    high_threshold: float
    bit_depth: int
    bg_enabled: bool

    @rd.reduce
    def set_black_level(piece: ImgConfigSlice, level: float) -> ImgConfigSlice:
        """Reducer to update black level of display an image comm"""
        if piece.white_level == level:
            return piece
        screen_bit_depth = 8
        fitted_black_level = min(level, piece.white_level)
        fitted_white_level = min(
            piece.white_level,
            level + screen_bit_depth / piece.bit_depth,
        )
        return piece.update(
            [
                (ImgConfigSlice.black_level, fitted_black_level),
                (ImgConfigSlice.white_level, fitted_white_level),
            ]
        )

    @rd.reduce
    def set_white_level(piece: ImgConfigSlice, level: float) -> ImgConfigSlice:
        if piece.black_level == level:
            return piece
        screen_bit_depth = 8
        fitted_white_level = max(level, piece.black_level)
        fitted_black_level = max(
            piece.black_level,
            level - screen_bit_depth / piece.bit_depth,
        )
        return piece.update(
            [
                (ImgConfigSlice.black_level, fitted_black_level),
                (ImgConfigSlice.white_level, fitted_white_level),
            ]
        )

    @rd.reduce
    def set_bit_depth(piece: ImgConfigSlice, bit_depth: int) -> ImgConfigSlice:
        screen_bit_depth = 8
        fitted_white_level = min(
            piece.white_level,
            piece.black_level + screen_bit_depth / bit_depth,
        )
        return piece.update(
            [(ImgConfigSlice.white_level, fitted_white_level)],
        )

    # @rd.extra_reduce(CameraSlice.bit_depth)
    # def set_bit_depth_extra(piece: ImgConfigSlice, bit_depth: int) -> ImgConfigSlice:
    #     return piece.set_bit_depth(bit_depth)

    @staticmethod
    def get_default_slice() -> ImgConfigSlice:
        return ImgConfigSlice(
            x=0,
            y=0,
            rotation=0,
            left_right_flip=False,
            top_bottom_flip=False,
            log_display=False,
            black_level=0.0,
            white_level=1.0,
            low_enabled=True,
            low_threshold=0.0,
            high_enabled=True,
            high_threshold=1.0,
            bit_depth=8,
            bg_enabled=False,
        )


class MyStore(rd.Store):
    camera: CameraSlice


store = MyStore(camera=CameraSlice.get_default_slice())
rd.create_store(store)


@rd.subscribe(CameraSlice.exposure_in_s)
def on_exposure_change(
    exp: float,
) -> None:
    """Callback function to handle exposure change."""


# endregion Slice


model = rd.get_store(MyStore)
valid = model.model_validate(rd.get_store())
print(valid)
