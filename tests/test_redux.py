"""This module contains tests for redux.py, a Redux-like state management library."""

# Access to a protected member _clear_store
# pylint: disable=W0212
# Unused argument fixtures
# pylint: disable=W0613
# Redefining name from outer scope (fixtures)
# pylint: disable=W0621
# Too many ancestors (8/7) (too-many-ancestors)
# pylint: disable=R0901

from __future__ import annotations

from typing import Annotated, Any, NamedTuple

import pytest
from annotated_types import Ge, Gt

import redux as rd

# region CameraSlice


class _Roi(NamedTuple):
    left: Annotated[int, Ge(0)]
    top: Annotated[int, Ge(0)]
    width: Annotated[int, Gt(0)]
    height: Annotated[int, Gt(0)]


class _BaseCameraSlice(rd.Slice):
    # name of the current camera, `camera_obj.device_info.name`
    name: str
    # id of the current camera, `camera_obj.device_info.id`
    camera_id: str


class _BitDepthSlice(rd.Slice):
    # bit depth of the captured image (8, 12, 14, 16)
    bit_depth: Annotated[int, Gt(0)]

    @rd.reduce
    def set_bit_depth(piece: _BitDepthSlice, payload: int) -> _BitDepthSlice:
        """set bit depth of the captured image"""
        ceil_payload = min(64, max(0, payload))
        return piece.update([(_BitDepthSlice.bit_depth, ceil_payload)])


class _RoiSlice(rd.Slice):
    # roi (left, top, width, height)
    roi: _Roi


class _ExposureSlice(rd.Slice):
    # exposure time in seconds
    exposure_in_s: Annotated[float, Gt(0)]

    @rd.reduce
    def set_exposure(piece: _ExposureSlice, payload: float) -> _ExposureSlice:
        """set exposure time in seconds"""
        return piece.update([(_ExposureSlice.exposure_in_s, min(100, max(0, payload)))])

    @rd.reduce
    def increment_exposure(piece: _ExposureSlice) -> _ExposureSlice:
        """increment exposure time in seconds"""
        return piece.update([(_ExposureSlice.exposure_in_s, piece.exposure_in_s + 1)])

    @rd.reduce
    def decrement_exposure(piece: _ExposureSlice) -> _ExposureSlice:
        """decrement exposure time in seconds"""
        return piece.update([(_ExposureSlice.exposure_in_s, piece.exposure_in_s - 1)])


class _CameraSlice(_BaseCameraSlice, _BitDepthSlice, _RoiSlice, _ExposureSlice):
    owner: str

    @staticmethod
    def get_default_slice() -> _CameraSlice:
        """Get default slice for camera."""
        return _CameraSlice(
            name="Camera",
            camera_id="camera_1",
            roi=_Roi(left=0, top=0, width=100, height=100),
            exposure_in_s=1.0,
            bit_depth=16,
            owner="owner_1",
        )


# endregion CameraSlice


# region ImgConfigSlice
class _ImgConfigSlice(rd.Slice):
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

    @rd.reduce
    def set_black_level(piece: _ImgConfigSlice, level: float) -> _ImgConfigSlice:
        """Reducer to update black level of display an image comm"""
        screen_bit_depth = 8
        fitted_black_level = min(level, piece.white_level)
        fitted_white_level = min(
            piece.white_level,
            level + screen_bit_depth / piece.bit_depth,
        )
        return piece.update(
            [
                (_ImgConfigSlice.black_level, fitted_black_level),
                (_ImgConfigSlice.white_level, fitted_white_level),
            ]
        )

    @rd.reduce
    def set_white_level(piece: _ImgConfigSlice, level: float) -> _ImgConfigSlice:
        """set white level of display an image"""
        screen_bit_depth = 8
        fitted_white_level = max(level, piece.black_level)
        fitted_black_level = max(
            piece.black_level,
            level - screen_bit_depth / piece.bit_depth,
        )
        return piece.update(
            [
                (_ImgConfigSlice.black_level, fitted_black_level),
                (_ImgConfigSlice.white_level, fitted_white_level),
            ]
        )

    @rd.reduce
    def set_bit_depth(piece: _ImgConfigSlice, bit_depth: int) -> _ImgConfigSlice:
        """set bit depth of display an image"""
        screen_bit_depth = 8
        fitted_white_level = min(
            piece.white_level,
            piece.black_level + screen_bit_depth / bit_depth,
        )
        return piece.update(
            [
                (_ImgConfigSlice.white_level, fitted_white_level),
                (_ImgConfigSlice.bit_depth, bit_depth),
            ],
        )

    @rd.reduce
    def set_roi(piece: _ImgConfigSlice, roi: _Roi) -> _ImgConfigSlice:
        """set roi"""
        return piece.update([(_ImgConfigSlice.roi, roi)])

    @rd.extra_reduce(_BitDepthSlice.bit_depth)
    def react_to_bit_depth(piece: _ImgConfigSlice, bit_depth: int) -> _ImgConfigSlice:
        """extra reducer to update bit depth"""
        return _ImgConfigSlice.set_bit_depth(piece, bit_depth)

    @rd.extra_reduce(_CameraSlice.exposure_in_s)
    def react_to_exposure(piece: _ImgConfigSlice) -> _ImgConfigSlice:
        """extra reducer to update exposure"""
        return piece.update(
            [
                (_ImgConfigSlice.bg_enabled, not piece.bg_enabled),
            ]
        )

    @staticmethod
    def get_default_slice() -> _ImgConfigSlice:
        """Get default slice for image configuration."""
        return _ImgConfigSlice(
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


class _ImgConfigExtra(_ImgConfigSlice):
    @rd.extra_reduce(_CameraSlice.roi)
    def react_to_roi(piece: _ImgConfigExtra, roi: _Roi) -> _ImgConfigExtra:
        """extra reducer to update roi"""
        return _ImgConfigExtra.model_validate(_ImgConfigSlice.set_roi(piece, roi))

    @rd.extra_reduce(_CameraSlice.exposure_in_s, _CameraSlice.bit_depth)
    def react_to_many(
        piece: _ImgConfigExtra, exposure: float, bit_depth: int
    ) -> _ImgConfigExtra:
        """extra reducer to update exposure and bit depth"""
        return piece.update(
            [
                (_ImgConfigSlice.black_level, exposure + bit_depth),
            ]
        )

    @staticmethod
    def get_default_slice() -> _ImgConfigExtra:
        """Get default slice for image configuration."""
        return _ImgConfigExtra(**_ImgConfigSlice.get_default_slice().model_dump())


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


class _Slice1(rd.Slice):
    state1: int = 0


class _Slice2(rd.Slice):
    state2: int = 0


class _Slice3(_Slice1):
    state3: int = 0


class _Slice4(_Slice3, _Slice2):
    state4: int = 0


class _Slice5(rd.Slice):
    state5: int = 0


class _Slice6(rd.Slice):
    state6: int = 0


class _Slice7(_Slice4, _Slice5, _Slice6):
    state7: int = 0

    @staticmethod
    def get_default_slice() -> _Slice7:
        """Get default slice."""
        return _Slice7(
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
def _store_with_camera() -> None:
    class _CameraStore(rd.Store):
        camera: _CameraSlice

    camera_store = _CameraStore(camera=_CameraSlice.get_default_slice())
    rd.create_store(camera_store, recreate=True)


@pytest.fixture()
def _store_with_img() -> None:
    class _ImgStore(rd.Store):
        img_config: _ImgConfigSlice

    img_store = _ImgStore(img_config=_ImgConfigSlice.get_default_slice())
    rd.create_store(img_store, recreate=True)


@pytest.fixture()
def _store_with_camera_img() -> None:
    class _CameraImgStore(rd.Store):
        camera: _CameraSlice
        img_config: _ImgConfigSlice

    camera_img_store = _CameraImgStore(
        camera=_CameraSlice.get_default_slice(), img_config=_ImgConfigSlice.get_default_slice()
    )
    rd.create_store(camera_img_store, recreate=True)


@pytest.fixture()
def _store_with_camera_img_extra() -> None:
    class _CameraImgStore(rd.Store):
        camera: _CameraSlice
        img_config: _ImgConfigExtra

    camera_img_store = _CameraImgStore(
        camera=_CameraSlice.get_default_slice(), img_config=_ImgConfigExtra.get_default_slice()
    )
    rd.create_store(camera_img_store, recreate=True)


@pytest.fixture()
def _store_with_multiple_inheritance() -> None:
    class _StoreWithMultipleInheritance(rd.Store):
        """Store with multiple inheritance."""

        slice7: _Slice7

    store = _StoreWithMultipleInheritance(slice7=_Slice7.get_default_slice())
    rd.create_store(store, recreate=True)


def test_create_store_one_slice_init(_store_with_camera) -> None:
    """Test creating a store with one slice."""
    default_camera = _CameraSlice.get_default_slice()

    assert rd.get_state(_CameraSlice.owner) == default_camera.owner
    assert rd.get_state(_CameraSlice.name) == default_camera.name
    assert rd.get_state(_CameraSlice.camera_id) == default_camera.camera_id
    assert rd.get_state(_CameraSlice.bit_depth) == default_camera.bit_depth
    assert rd.get_state(_CameraSlice.roi) == default_camera.roi
    assert rd.get_state(_CameraSlice.exposure_in_s) == default_camera.exposure_in_s

    assert rd.get_state(_BaseCameraSlice.camera_id) == default_camera.camera_id
    assert rd.get_state(_BaseCameraSlice.name) == default_camera.name
    assert rd.get_state(_BitDepthSlice.bit_depth) == default_camera.bit_depth
    assert rd.get_state(_RoiSlice.roi) == default_camera.roi
    assert rd.get_state(_ExposureSlice.exposure_in_s) == default_camera.exposure_in_s


def test_extra_reducer_init(_store_with_camera_img) -> None:
    """Test creating a store with extra reducer."""
    default_camera = _CameraSlice.get_default_slice()
    assert rd.get_state(_CameraSlice.bit_depth) == default_camera.bit_depth
    assert rd.get_state(_BitDepthSlice.bit_depth) == default_camera.bit_depth
    assert rd.get_state(_ImgConfigSlice.bit_depth) == default_camera.bit_depth


def test_slice_name_attr() -> None:
    """Test that the slice name is set correctly."""
    assert _CameraSlice.slice_name == "_CameraSlice"  # pylint: disable=W0143
    camera_slice = _CameraSlice.get_default_slice()
    assert camera_slice.slice_name == "_CameraSlice"


@pytest.mark.parametrize(
    "attr_path, state_path, state_value",
    [
        (_Slice7.state1, _Slice7.state1, _Slice7.get_default_slice().state1),
        (_Slice7.state2, _Slice7.state2, _Slice7.get_default_slice().state2),
        (_Slice7.state3, _Slice7.state3, _Slice7.get_default_slice().state3),
        (_Slice7.state4, _Slice7.state4, _Slice7.get_default_slice().state4),
        (_Slice7.state5, _Slice7.state5, _Slice7.get_default_slice().state5),
        (_Slice7.state6, _Slice7.state6, _Slice7.get_default_slice().state6),
        (_Slice7.state7, _Slice7.state7, _Slice7.get_default_slice().state7),
        (_Slice6.state6, _Slice6.state6, _Slice7.get_default_slice().state6),
        (_Slice5.state5, _Slice5.state5, _Slice7.get_default_slice().state5),
        (_Slice4.state4, _Slice4.state4, _Slice7.get_default_slice().state4),
        (_Slice3.state3, _Slice3.state3, _Slice7.get_default_slice().state3),
        (_Slice2.state2, _Slice2.state2, _Slice7.get_default_slice().state2),
        (_Slice1.state1, _Slice1.state1, _Slice7.get_default_slice().state1),
        (_Slice4.state3, _Slice4.state3, _Slice7.get_default_slice().state3),
        (_Slice4.state2, _Slice4.state2, _Slice7.get_default_slice().state2),
        (_Slice4.state1, _Slice4.state1, _Slice7.get_default_slice().state1),
        (_Slice3.state1, _Slice3.state1, _Slice7.get_default_slice().state1),
    ],
)
def test__store_with_multiple_inheritance(
    _store_with_multiple_inheritance,
    attr_path: Any,
    state_path: rd.slice.StatePath,
    state_value: Any,
) -> None:
    """Test that the store with multiple inheritance is created correctly."""
    assert rd.get_state(attr_path) == state_value
    assert rd.get_state(state_path) == state_value


def test_one_directional_extra_reduce(_store_with_camera_img) -> None:
    """Test that the extra reducer only updates the state in one direction."""
    bit_depth = _CameraSlice.get_default_slice().bit_depth
    assert rd.get_state(_CameraSlice.bit_depth) == bit_depth
    assert rd.get_state(_BitDepthSlice.bit_depth) == bit_depth
    assert rd.get_state(_ImgConfigSlice.bit_depth) == bit_depth

    new_bit_depth = bit_depth * 2
    rd.dispatch_state(_ImgConfigSlice.bit_depth, new_bit_depth)
    assert rd.get_state(_CameraSlice.bit_depth) == bit_depth
    assert rd.get_state(_BitDepthSlice.bit_depth) == bit_depth
    assert rd.get_state(_ImgConfigSlice.bit_depth) == new_bit_depth


@pytest.mark.parametrize(
    "state_path",
    [_CameraSlice.bit_depth, _BitDepthSlice.bit_depth],
)
def test_dispatch_bit_depth_state(
    _store_with_camera_img, state_path: rd.slice.StatePath
) -> None:
    """Test that the dispatch of bit depth state works correctly."""
    bit_depth = _CameraSlice.get_default_slice().bit_depth
    assert rd.get_state(_CameraSlice.bit_depth) == bit_depth
    assert rd.get_state(_BitDepthSlice.bit_depth) == bit_depth
    assert rd.get_state(_ImgConfigSlice.bit_depth) == bit_depth

    bit_depth *= 2
    rd.dispatch_state(state_path, bit_depth)
    assert rd.get_state(_CameraSlice.bit_depth) == bit_depth
    assert rd.get_state(_BitDepthSlice.bit_depth) == bit_depth
    assert rd.get_state(_ImgConfigSlice.bit_depth) == bit_depth


def test_dispatch_set_bit_depth(_store_with_camera_img) -> None:
    """Test that the dispatch of set bit depth works correctly."""
    bit_depth = _CameraSlice.get_default_slice().bit_depth
    assert rd.get_state(_CameraSlice.bit_depth) == bit_depth
    assert rd.get_state(_BitDepthSlice.bit_depth) == bit_depth
    assert rd.get_state(_ImgConfigSlice.bit_depth) == bit_depth

    bit_depth *= 2
    rd.dispatch(_BitDepthSlice.set_bit_depth, bit_depth)
    assert rd.get_state(_CameraSlice.bit_depth) == bit_depth
    assert rd.get_state(_BitDepthSlice.bit_depth) == bit_depth
    assert rd.get_state(_ImgConfigSlice.bit_depth) == bit_depth

    bit_depth //= 2
    rd.dispatch(_CameraSlice.set_bit_depth, int(bit_depth))
    assert rd.get_state(_CameraSlice.bit_depth) == bit_depth
    assert rd.get_state(_BitDepthSlice.bit_depth) == bit_depth
    assert rd.get_state(_ImgConfigSlice.bit_depth) == bit_depth

    bit_depth = 100
    rd.dispatch(_CameraSlice.set_bit_depth, bit_depth)
    assert rd.get_state(_CameraSlice.bit_depth) == 64
    assert rd.get_state(_BitDepthSlice.bit_depth) == 64
    assert rd.get_state(_ImgConfigSlice.bit_depth) == 64


def test_incremental_reducers(_store_with_camera_img) -> None:
    """Test that the incremental reducers work correctly."""
    default_camera = _CameraSlice.get_default_slice()
    assert rd.get_state(_CameraSlice.exposure_in_s) == default_camera.exposure_in_s

    rd.dispatch(_ExposureSlice.increment_exposure)
    assert rd.get_state(_CameraSlice.exposure_in_s) == default_camera.exposure_in_s + 1

    rd.dispatch(_CameraSlice.decrement_exposure)
    assert rd.get_state(_CameraSlice.exposure_in_s) == default_camera.exposure_in_s + 1 - 1


def test_extra_reducer_no_args(_store_with_camera_img) -> None:
    """Test that the extra reducer works correctly."""
    default_camera = _CameraSlice.get_default_slice()
    default_img = _ImgConfigSlice.get_default_slice()
    assert rd.get_state(_CameraSlice.exposure_in_s) == default_camera.exposure_in_s

    rd.dispatch(_ExposureSlice.set_exposure, 1.0)
    not_default_bg: bool = not default_img.bg_enabled
    assert rd.get_state(_ImgConfigSlice.bg_enabled) == not_default_bg


def test_subscribe(_store_with_camera_img) -> None:
    """Test that the subscribe function works correctly."""
    bit_depths: list[int] = []
    init_bit_depth = _CameraSlice.get_default_slice().bit_depth

    def img_bit_depth(val: int) -> None:
        bit_depths.append(val)

    unsubscribe = rd.subscribe(_ImgConfigSlice.bit_depth)(img_bit_depth)

    assert bit_depths == [init_bit_depth]
    rd.dispatch(_ImgConfigSlice.set_bit_depth, 10)
    assert bit_depths == [init_bit_depth, 10]
    rd.dispatch_state(_ImgConfigSlice.bit_depth, 20)
    assert bit_depths == [init_bit_depth, 10, 20]

    rd.dispatch(_CameraSlice.set_bit_depth, 30)
    assert bit_depths == [init_bit_depth, 10, 20, 30]
    rd.dispatch_state(_CameraSlice.bit_depth, 40)
    assert bit_depths == [init_bit_depth, 10, 20, 30, 40]
    rd.dispatch(_BitDepthSlice.set_bit_depth, 50)
    assert bit_depths == [init_bit_depth, 10, 20, 30, 40, 50]
    rd.dispatch_state(_BitDepthSlice.bit_depth, 60)
    assert bit_depths == [init_bit_depth, 10, 20, 30, 40, 50, 60]

    unsubscribe()

    rd.dispatch(_ImgConfigSlice.set_bit_depth, 70)
    assert bit_depths == [init_bit_depth, 10, 20, 30, 40, 50, 60]


def test_update_no_change_value(_store_with_camera_img) -> None:
    """Test that the update function does not trigger a change when the value is the same."""
    bit_depths: list[int] = []
    init_bit_depth = _CameraSlice.get_default_slice().bit_depth

    @rd.subscribe(_ImgConfigSlice.bit_depth)
    def img_bit_depth(val: int) -> None:
        bit_depths.append(val)

    assert bit_depths == [init_bit_depth]

    rd.dispatch(_ImgConfigSlice.set_bit_depth, init_bit_depth)
    assert bit_depths == [init_bit_depth]

    rd.dispatch_state(_ImgConfigSlice.bit_depth, init_bit_depth * 2)
    assert bit_depths == [init_bit_depth, init_bit_depth * 2]
    rd.dispatch_state(_ImgConfigSlice.bit_depth, init_bit_depth * 2)
    assert bit_depths == [init_bit_depth, init_bit_depth * 2]


def test_interdependent_update(_store_with_camera_img) -> None:
    """Test that the interdependent update works correctly."""
    rd.dispatch_state(_CameraSlice.bit_depth, 8)
    rd.dispatch_state(_ImgConfigSlice.black_level, 0)
    rd.dispatch_state(_ImgConfigSlice.white_level, 1)

    assert rd.get_state(_ImgConfigSlice.black_level) == 0
    assert rd.get_state(_ImgConfigSlice.white_level) == 1

    rd.dispatch(_ImgConfigSlice.set_black_level, 0.5)
    assert rd.get_state(_ImgConfigSlice.black_level) == 0.5
    assert rd.get_state(_ImgConfigSlice.white_level) == 1.0

    rd.dispatch(_ImgConfigSlice.set_white_level, 0.3)
    assert rd.get_state(_ImgConfigSlice.black_level) == 0.5
    assert rd.get_state(_ImgConfigSlice.white_level) == 0.5


def test_extra_reduce_subscribe_parent(_store_with_camera_img_extra) -> None:
    """Test that the extra reducer works correctly when subscribing to a parent slice."""
    roi_log: list[_Roi] = []
    init_roi = _CameraSlice.get_default_slice().roi

    def img_roi(val: _Roi) -> None:
        roi_log.append(val)

    unsubscribe = rd.subscribe(_ImgConfigSlice.roi)(img_roi)

    assert roi_log == [init_roi]
    rd.dispatch_state(_CameraSlice.roi, _Roi(0, 0, 200, 200))
    assert roi_log == [init_roi, _Roi(0, 0, 200, 200)]
    rd.dispatch_state(_ImgConfigSlice.roi, _Roi(0, 0, 300, 300))
    assert roi_log == [init_roi, _Roi(0, 0, 200, 200), _Roi(0, 0, 300, 300)]

    unsubscribe()
    rd.dispatch_state(_CameraSlice.roi, _Roi(0, 0, 400, 400))
    assert roi_log == [init_roi, _Roi(0, 0, 200, 200), _Roi(0, 0, 300, 300)]

    rd.dispatch_state(_CameraSlice.exposure_in_s, 1.0)
    rd.dispatch_state(_CameraSlice.bit_depth, 8)
    assert rd.get_state(_ImgConfigSlice.black_level) == 9


def test_multiple_unsubscribe(_store_with_img) -> None:
    """Test that multiple unsubscribe works correctly."""
    unsubscribes: list = []

    for attr in ["x", "y", "rotation"]:
        unsubscribes.append(
            rd.subscribe(rd.build_path("_ImgConfigSlice", attr))(lambda val: None)
        )

    for unsubscribe in unsubscribes:
        unsubscribe()


def test_invalid_extra_reduce() -> None:
    """Test that extra_reduce raises an error when the state is not found."""
    with pytest.raises(ValueError):

        @rd.extra_reduce()  # type: ignore
        def invalid_extra_reducer() -> None: ...


def test_invalid_create_store() -> None:
    """Test creating a store with an invalid store."""
    rd.store._clear_store()
    with pytest.raises(TypeError):
        rd.create_store(_CameraSlice)  # type: ignore


def test_invalid_get_state() -> None:
    """Test that get_state raises an error when the state is not found."""
    rd.store._clear_store()
    with pytest.raises(RuntimeError):
        rd.get_state(rd.build_path("_CameraSlice", "wrong_state"))

    with pytest.raises(RuntimeError):
        rd.get_state(rd.build_path("WrongSlice", "wrong_state"))
