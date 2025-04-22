from __future__ import annotations

from typing import Annotated, Generator, NamedTuple, Any
from annotated_types import Gt, Ge
import pytest

import pyrux as pr


# region CameraSlice


class _Roi(NamedTuple):
    left: Annotated[int, Ge(0)]
    top: Annotated[int, Ge(0)]
    width: Annotated[int, Gt(0)]
    height: Annotated[int, Gt(0)]


class BaseCameraSlice(pr.Slice):
    # name of the current camera, `camera_obj.device_info.name`
    name: str
    # id of the current camera, `camera_obj.device_info.id`
    camera_id: str


class BitDepthSlice(pr.Slice):
    # bit depth of the captured image (8, 12, 14, 16)
    bit_depth: Annotated[int, Gt(0)]

    @pr.reduce
    def set_bit_depth(piece: BitDepthSlice, payload: int) -> BitDepthSlice:
        ceil_payload = min(64, max(0, payload))
        return piece.update([(BitDepthSlice.bit_depth, ceil_payload)])


class RoiSlice(pr.Slice):
    # roi (left, top, width, height)
    roi: _Roi


class ExposureSlice(pr.Slice):
    # exposure time in seconds
    exposure_in_s: Annotated[float, Gt(0)]

    @pr.reduce
    def set_exposure(piece: ExposureSlice, payload: float) -> ExposureSlice:
        return piece.update([(ExposureSlice.exposure_in_s, min(100, max(0, payload)))])

    @pr.reduce
    def increment_exposure(piece: ExposureSlice) -> ExposureSlice:
        return piece.update([(ExposureSlice.exposure_in_s, piece.exposure_in_s + 1)])
    
    @pr.reduce
    def decrement_exposure(piece: ExposureSlice) -> ExposureSlice:
        return piece.update([(ExposureSlice.exposure_in_s, piece.exposure_in_s - 1)])

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


# endregion CameraSlice


# region ImgConfigSlice
class ImgConfigSlice(pr.Slice):
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
    roi: _Roi

    @pr.reduce
    def set_black_level(piece: ImgConfigSlice, level: float) -> ImgConfigSlice:
        """Reducer to update black level of display an image comm"""
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

    @pr.reduce
    def set_white_level(piece: ImgConfigSlice, level: float) -> ImgConfigSlice:
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

    @pr.reduce
    def set_bit_depth(piece: ImgConfigSlice, bit_depth: int) -> ImgConfigSlice:
        screen_bit_depth = 8
        fitted_white_level = min(
            piece.white_level,
            piece.black_level + screen_bit_depth / bit_depth,
        )
        return piece.update(
            [
                (ImgConfigSlice.white_level, fitted_white_level),
                (ImgConfigSlice.bit_depth, bit_depth),
            ],
        )

    @pr.reduce
    def set_roi(piece: ImgConfigSlice, roi: _Roi) -> ImgConfigSlice:
        return piece.update([(ImgConfigSlice.roi, roi)])

    @pr.extra_reduce(BitDepthSlice.bit_depth)
    def react_to_bit_depth(piece: ImgConfigSlice, bit_depth: int) -> ImgConfigSlice:
        return ImgConfigSlice.set_bit_depth(piece, bit_depth)

    @pr.extra_reduce(CameraSlice.exposure_in_s)
    def react_to_exposure(piece: ImgConfigSlice) -> ImgConfigSlice:
        return piece.update([
            (ImgConfigSlice.bg_enabled, not piece.bg_enabled),
        ])

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
            roi=_Roi(left=0, top=0, width=100, height=100),
        )


class ImgConfigExtra(ImgConfigSlice):
    @pr.extra_reduce(CameraSlice.roi)
    def react_to_roi(piece: ImgConfigExtra, roi: _Roi) -> ImgConfigExtra:
        return ImgConfigExtra.model_validate(ImgConfigSlice.set_roi(piece, roi))

# endregion ImgConfigSlice


# region Slices
# This region contain slices that multiple inherit from other slices
# 7
# ├── 6
# ├── 5
# └── 4
#     ├── 3
#     │   └── 1
#     └── 2


class Slice1(pr.Slice):
    state1: int = 0


class Slice2(pr.Slice):
    state2: int = 0


class Slice3(Slice1):
    state3: int = 0


class Slice4(Slice3, Slice2):
    state4: int = 0


class Slice5(pr.Slice):
    state5: int = 0


class Slice6(pr.Slice):
    state6: int = 0


class Slice7(Slice4, Slice5, Slice6):
    state7: int = 0

    @staticmethod
    def get_default_slice() -> Slice7:
        return Slice7(
            state1=1,
            state2=2,
            state3=3,
            state4=4,
            state5=5,
            state6=6,
            state7=7,
        )


# endregion Slices


# region Tests


@pytest.fixture()
def store_with_camera() -> Generator[None, None, None]:
    default_camera = CameraSlice.get_default_slice()
    pr.create_store([default_camera])
    yield
    pr.clear_store()


@pytest.fixture()
def store_with_camera_img() -> Generator[None, None, None]:
    default_camera = CameraSlice.get_default_slice()
    default_img_config = ImgConfigSlice.get_default_slice()
    pr.create_store([default_camera, default_img_config])
    yield
    pr.clear_store()


@pytest.fixture()
def store_with_multiple_inheritance() -> Generator[None, None, None]:
    pr.create_store([Slice7.get_default_slice()])
    yield
    pr.clear_store()


def test_create_store_one_slice_init(store_with_camera):
    default_camera = CameraSlice.get_default_slice()

    assert pr.get_state(CameraSlice.owner) == default_camera.owner
    assert pr.get_state(CameraSlice.name) == default_camera.name
    assert pr.get_state(CameraSlice.camera_id) == default_camera.camera_id
    assert pr.get_state(CameraSlice.bit_depth) == default_camera.bit_depth
    assert pr.get_state(CameraSlice.roi) == default_camera.roi
    assert pr.get_state(CameraSlice.exposure_in_s) == default_camera.exposure_in_s

    assert pr.get_state(BaseCameraSlice.camera_id) == default_camera.camera_id
    assert pr.get_state(BaseCameraSlice.name) == default_camera.name
    assert pr.get_state(BitDepthSlice.bit_depth) == default_camera.bit_depth
    assert pr.get_state(RoiSlice.roi) == default_camera.roi
    assert pr.get_state(ExposureSlice.exposure_in_s) == default_camera.exposure_in_s


def test_extra_reducer_init(store_with_camera_img):
    default_camera = CameraSlice.get_default_slice()
    assert pr.get_state(CameraSlice.bit_depth) == default_camera.bit_depth
    assert pr.get_state(BitDepthSlice.bit_depth) == default_camera.bit_depth
    assert pr.get_state(ImgConfigSlice.bit_depth) == default_camera.bit_depth


def test_slice_name_attr():
    assert CameraSlice.slice_name == "CameraSlice"
    camera_slice = CameraSlice.get_default_slice()
    assert camera_slice.slice_name == "CameraSlice"


@pytest.mark.parametrize(
    "attr_path, state_path, state_value",
    [
        (Slice7.state1, Slice7.state1, Slice7.get_default_slice().state1),
        (Slice7.state2, Slice7.state2, Slice7.get_default_slice().state2),
        (Slice7.state3, Slice7.state3, Slice7.get_default_slice().state3),
        (Slice7.state4, Slice7.state4, Slice7.get_default_slice().state4),
        (Slice7.state5, Slice7.state5, Slice7.get_default_slice().state5),
        (Slice7.state6, Slice7.state6, Slice7.get_default_slice().state6),
        (Slice7.state7, Slice7.state7, Slice7.get_default_slice().state7),
        (Slice6.state6, Slice6.state6, Slice7.get_default_slice().state6),
        (Slice5.state5, Slice5.state5, Slice7.get_default_slice().state5),
        (Slice4.state4, Slice4.state4, Slice7.get_default_slice().state4),
        (Slice3.state3, Slice3.state3, Slice7.get_default_slice().state3),
        (Slice2.state2, Slice2.state2, Slice7.get_default_slice().state2),
        (Slice1.state1, Slice1.state1, Slice7.get_default_slice().state1),
        (Slice4.state3, Slice4.state3, Slice7.get_default_slice().state3),
        (Slice4.state2, Slice4.state2, Slice7.get_default_slice().state2),
        (Slice4.state1, Slice4.state1, Slice7.get_default_slice().state1),
        (Slice3.state1, Slice3.state1, Slice7.get_default_slice().state1),
    ]
)
def test_store_with_multiple_inheritance(
    store_with_multiple_inheritance,
    attr_path: Any,
    state_path: pr.slice.StatePath,
    state_value: Any,
):
    assert pr.get_state(attr_path) == state_value
    assert pr.get_state(state_path) == state_value

def test_one_directional_extra_reduce(store_with_camera_img):
    bit_depth = CameraSlice.get_default_slice().bit_depth
    assert pr.get_state(CameraSlice.bit_depth) == bit_depth
    assert pr.get_state(BitDepthSlice.bit_depth) == bit_depth
    assert pr.get_state(ImgConfigSlice.bit_depth) == bit_depth

    new_bit_depth = bit_depth * 2
    pr.dispatch_state(ImgConfigSlice.bit_depth, new_bit_depth)
    assert pr.get_state(CameraSlice.bit_depth) == bit_depth
    assert pr.get_state(BitDepthSlice.bit_depth) == bit_depth
    assert pr.get_state(ImgConfigSlice.bit_depth) == new_bit_depth


@pytest.mark.parametrize(
    "state_path",
    [CameraSlice.bit_depth, BitDepthSlice.bit_depth],
)
def test_dispatch_bit_depth_state(store_with_camera_img, state_path: pr.slice.StatePath):
    bit_depth = CameraSlice.get_default_slice().bit_depth
    assert pr.get_state(CameraSlice.bit_depth) == bit_depth
    assert pr.get_state(BitDepthSlice.bit_depth) == bit_depth
    assert pr.get_state(ImgConfigSlice.bit_depth) == bit_depth

    bit_depth *= 2
    pr.dispatch_state(state_path, bit_depth)
    assert pr.get_state(CameraSlice.bit_depth) == bit_depth
    assert pr.get_state(BitDepthSlice.bit_depth) == bit_depth
    assert pr.get_state(ImgConfigSlice.bit_depth) == bit_depth


def test_dispatch_set_bit_depth(store_with_camera_img):
    bit_depth = CameraSlice.get_default_slice().bit_depth
    assert pr.get_state(CameraSlice.bit_depth) == bit_depth
    assert pr.get_state(BitDepthSlice.bit_depth) == bit_depth
    assert pr.get_state(ImgConfigSlice.bit_depth) == bit_depth

    bit_depth *= 2
    pr.dispatch(BitDepthSlice.set_bit_depth, bit_depth)
    assert pr.get_state(CameraSlice.bit_depth) == bit_depth
    assert pr.get_state(BitDepthSlice.bit_depth) == bit_depth
    assert pr.get_state(ImgConfigSlice.bit_depth) == bit_depth

    bit_depth /= 2
    pr.dispatch(CameraSlice.set_bit_depth, int(bit_depth))
    assert pr.get_state(CameraSlice.bit_depth) == bit_depth
    assert pr.get_state(BitDepthSlice.bit_depth) == bit_depth
    assert pr.get_state(ImgConfigSlice.bit_depth) == bit_depth

    bit_depth = 100
    pr.dispatch(CameraSlice.set_bit_depth, bit_depth)
    assert pr.get_state(CameraSlice.bit_depth) == 64
    assert pr.get_state(BitDepthSlice.bit_depth) == 64
    assert pr.get_state(ImgConfigSlice.bit_depth) == 64

def test_incremental_reducers(store_with_camera_img):
    default_camera = CameraSlice.get_default_slice()
    assert pr.get_state(CameraSlice.exposure_in_s) == default_camera.exposure_in_s

    pr.dispatch(ExposureSlice.increment_exposure)
    assert pr.get_state(CameraSlice.exposure_in_s) == default_camera.exposure_in_s + 1

    pr.dispatch(CameraSlice.decrement_exposure)
    assert pr.get_state(CameraSlice.exposure_in_s) == default_camera.exposure_in_s + 1 - 1

def test_extra_reducer_no_args(store_with_camera_img):
    default_camera = CameraSlice.get_default_slice()
    default_img = ImgConfigSlice.get_default_slice()
    assert pr.get_state(CameraSlice.exposure_in_s) == default_camera.exposure_in_s

    pr.dispatch(ExposureSlice.set_exposure, 1.0)
    assert pr.get_state(ImgConfigSlice.bg_enabled) == default_img.bg_enabled


def test_subscribe(store_with_camera_img):
    bit_depths: list[int] = []
    init_bit_depth = CameraSlice.get_default_slice().bit_depth

    def img_bit_depth(val: int) -> None:
        bit_depths.append(val)

    unsubscribe = pr.subscribe(ImgConfigSlice.bit_depth)(img_bit_depth)

    assert bit_depths == [init_bit_depth]
    pr.dispatch(ImgConfigSlice.set_bit_depth, 10)
    assert bit_depths == [init_bit_depth, 10]
    pr.dispatch_state(ImgConfigSlice.bit_depth, 20)
    assert bit_depths == [init_bit_depth, 10, 20]

    pr.dispatch(CameraSlice.set_bit_depth, 30)
    assert bit_depths == [init_bit_depth, 10, 20, 30]
    pr.dispatch_state(CameraSlice.bit_depth, 40)
    assert bit_depths == [init_bit_depth, 10, 20, 30, 40]
    pr.dispatch(BitDepthSlice.set_bit_depth, 50)
    assert bit_depths == [init_bit_depth, 10, 20, 30, 40, 50]
    pr.dispatch_state(BitDepthSlice.bit_depth, 60)
    assert bit_depths == [init_bit_depth, 10, 20, 30, 40, 50, 60]

    unsubscribe()

    pr.dispatch(ImgConfigSlice.set_bit_depth, 70)
    assert bit_depths == [init_bit_depth, 10, 20, 30, 40, 50, 60]

def test_update_no_change_value(store_with_camera_img):
    bit_depths: list[int] = []
    init_bit_depth = CameraSlice.get_default_slice().bit_depth

    @pr.subscribe(ImgConfigSlice.bit_depth)
    def img_bit_depth(val: int) -> None:
        bit_depths.append(val)

    assert bit_depths == [init_bit_depth]

    pr.dispatch(ImgConfigSlice.set_bit_depth, init_bit_depth)
    assert bit_depths == [init_bit_depth]

    pr.dispatch_state(ImgConfigSlice.bit_depth, init_bit_depth * 2)
    assert bit_depths == [init_bit_depth, init_bit_depth * 2]
    pr.dispatch_state(ImgConfigSlice.bit_depth, init_bit_depth * 2)
    assert bit_depths == [init_bit_depth, init_bit_depth * 2]

def test_interdependent_update(store_with_camera_img):
    pr.dispatch_state(CameraSlice.bit_depth, 8)
    pr.dispatch_state(ImgConfigSlice.black_level, 0)
    pr.dispatch_state(ImgConfigSlice.white_level, 1)

    assert pr.get_state(ImgConfigSlice.black_level) == 0
    assert pr.get_state(ImgConfigSlice.white_level) == 1

    pr.dispatch(ImgConfigSlice.set_black_level, 0.5)
    assert pr.get_state(ImgConfigSlice.black_level) == 0.5
    assert pr.get_state(ImgConfigSlice.white_level) == 1.0

    pr.dispatch(ImgConfigSlice.set_white_level, 0.3)
    assert pr.get_state(ImgConfigSlice.black_level) == 0.5
    assert pr.get_state(ImgConfigSlice.white_level) == 0.5

def test_extra_reduce_subscribe_parent(store_with_camera_img):
    roi_log: list[_Roi] = []
    init_roi = CameraSlice.get_default_slice().roi

    def img_roi(val: _Roi) -> None:
        roi_log.append(val)

    unsubscribe = pr.subscribe(ImgConfigSlice.roi)(img_roi)

    assert roi_log == [init_roi]
    # pr.dispatch(ImgConfigSlice.set_bit_depth, 10)
    # assert bit_depths == [init_bit_depth, 10]
    # pr.dispatch_state(ImgConfigSlice.bit_depth, 20)
    # assert bit_depths == [init_bit_depth, 10, 20]

    # pr.dispatch(CameraSlice.set_bit_depth, 30)
    # assert bit_depths == [init_bit_depth, 10, 20, 30]
    # pr.dispatch_state(CameraSlice.bit_depth, 40)
    # assert bit_depths == [init_bit_depth, 10, 20, 30, 40]
    # pr.dispatch(BitDepthSlice.set_bit_depth, 50)
    # assert bit_depths == [init_bit_depth, 10, 20, 30, 40, 50]
    # pr.dispatch_state(BitDepthSlice.bit_depth, 60)
    # assert bit_depths == [init_bit_depth, 10, 20, 30, 40, 50, 60]

    unsubscribe()

    # pr.dispatch(ImgConfigSlice.set_bit_depth, 70)
    # assert bit_depths == [init_bit_depth, 10, 20, 30, 40, 50, 60]

def test_dump_store(store_with_camera):
    store = pr.dump_store()
    assert len(store) == 1
    assert store["CameraSlice"] == CameraSlice.get_default_slice().model_dump()

def test_get_store(store_with_camera):
    store = pr.get_store()
    assert len(store) == 1
    assert store["CameraSlice"].model_dump() == CameraSlice.get_default_slice().model_dump()

def test_invalid_extra_reduce():
    with pytest.raises(ValueError):
        @pr.extra_reduce()  # type: ignore
        def invalid_extra_reducer() -> None: ...

def test_invalid_create_store():
    with pytest.raises(TypeError):
        pr.create_store([CameraSlice, CameraSlice])  # type: ignore

def test_invalid_get_state():
    with pytest.raises(KeyError):
        pr.get_state(pr.build_path("CameraSlice", "wrong_state"))

    with pytest.raises(KeyError):
        pr.get_state(pr.build_path("WrongSlice", "wrong_state"))


