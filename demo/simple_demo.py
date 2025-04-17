from __future__ import annotations

from typing import Annotated, Literal

from annotated_types import Gt, Ge, Le

import pyrux as pr


class CameraSettings(pr.Slice):
    # name and id of the current camera, `camera_obj.device_info`
    camera_name: str
    camera_id: str
    # exposure time in seconds
    exposure_in_s: Annotated[float, Gt(0)]
    # gain without normalization
    gain: float
    # binning value, (horizontal, vertical)
    binning: tuple[Annotated[int, Gt(0)], Annotated[int, Gt(0)]]
    # trigger settings
    trigger_mode: int
    number_of_frames_per_burst: int
    # bit depth of the captured image (8, 12, 14, 16)
    bit_depth: Literal[8, 16]
    # roi (left, top, width, height)
    roi: tuple[
        Annotated[int, Ge(0)],
        Annotated[int, Ge(0)],
        Annotated[int, Gt(0)],
        Annotated[int, Gt(0)],
    ]
    # offset without normalization
    offset: Annotated[float, Ge(0)]
    readout_speed: int

    @pr.reduce
    def set_exposure(piece: CameraSettings, payload: float) -> CameraSettings:
        return piece.update([(CameraSettings.exposure_in_s, payload)])

    @pr.reduce
    def increment_gain(piece: CameraSettings) -> CameraSettings:
        return piece.update([(CameraSettings.gain, piece.gain + 1)])

    @pr.reduce
    def decrement_gain(piece: CameraSettings) -> CameraSettings:
        return piece.update([(CameraSettings.gain, piece.gain - 1)])

    @pr.reduce
    def change_binning(piece: CameraSettings, payload: tuple[int, int]) -> CameraSettings:
        return piece.update([(CameraSettings.binning, payload)])

    @pr.reduce
    def change_roi(
        piece: CameraSettings, payload: tuple[int, int, int, int]
    ) -> CameraSettings:
        return piece.update([(CameraSettings.roi, payload)])

    @pr.reduce
    def set_bit_depth(piece: CameraSettings, payload: Literal[8, 16]) -> CameraSettings:
        return piece.update([(CameraSettings.bit_depth, payload)])


Grey8bit = Annotated[int, Ge(0), Le(255)]
Color = tuple[Grey8bit, Grey8bit, Grey8bit, Grey8bit]


class MonoImgSettings(pr.Slice):
    x: float
    y: float
    rotation: float
    left_right_flip: bool
    top_bottom_flip: bool
    log_display: bool
    tint: Color
    black_level: float
    white_level: float
    low_enabled: bool
    low_threshold: float
    high_enabled: bool
    high_threshold: float
    low_range_mask: Color
    mid_range_mask: Color
    high_range_mask: Color

    @pr.reduce
    def flip_horizontal(piece: MonoImgSettings) -> MonoImgSettings:
        return piece.update([(MonoImgSettings.left_right_flip, not piece.left_right_flip)])

    @pr.reduce
    def set_black_level(piece: MonoImgSettings, payload: float) -> MonoImgSettings:
        if payload <= piece.white_level:
            return piece.update([(MonoImgSettings.black_level, payload)])
        else:
            return piece.update(
                [
                    (MonoImgSettings.black_level, piece.white_level),
                    (MonoImgSettings.white_level, piece.white_level),
                ]
            )

    @pr.reduce
    def set_white_level(piece: MonoImgSettings, payload: float) -> MonoImgSettings:
        if payload >= piece.black_level:
            return piece.update([(MonoImgSettings.white_level, payload)])
        else:
            return piece.update(
                [
                    (MonoImgSettings.white_level, piece.black_level),
                    (MonoImgSettings.black_level, piece.black_level),
                ]
            )

    @pr.extra_reduce(CameraSettings.roi)
    def react_to_roi(
        piece: MonoImgSettings, state: tuple[int, int, int, int]
    ) -> MonoImgSettings:
        return piece.update(
            [
                (MonoImgSettings.black_level, piece.black_level / state[2]),
            ]
        )

    @pr.extra_reduce(CameraSettings.exposure_in_s, CameraSettings.binning)
    def react_to_exposure_gain(
        piece: MonoImgSettings, exposure: float, binning: tuple[int, int]
    ) -> MonoImgSettings:
        return piece.update(
            [
                (MonoImgSettings.black_level, piece.black_level * exposure / binning[0]),
                (MonoImgSettings.white_level, piece.white_level * exposure / binning[1]),
            ]
        )


pr.create_store(
    [
        CameraSettings(
            camera_name="Camera",
            camera_id="Camera ID",
            exposure_in_s=0.1,
            gain=0.0,
            binning=(1, 1),
            trigger_mode=0,
            number_of_frames_per_burst=1,
            bit_depth=16,
            roi=(0, 0, 100, 100),
            offset=0.0,
            readout_speed=1,
        ),
        MonoImgSettings(
            x=0.0,
            y=0.0,
            rotation=0.0,
            left_right_flip=False,
            top_bottom_flip=False,
            log_display=False,
            tint=(0, 0, 0, 0),
            black_level=0.0,
            white_level=1.0,
            low_enabled=False,
            low_threshold=0.0,
            high_enabled=False,
            high_threshold=1.0,
            low_range_mask=(255, 255, 255, 255),
            mid_range_mask=(255, 255, 255, 255),
            high_range_mask=(255, 255, 255, 255),
        ),
    ]
)


@pr.subscribe(CameraSettings.bit_depth, MonoImgSettings.black_level)
def react_to_black_change(bit_depth: int, black_level: float) -> None:
    print(f"black block to {int(black_level * (2**bit_depth - 1))}")


@pr.subscribe(CameraSettings.bit_depth, MonoImgSettings.white_level)
def react_to_white_change(bit_depth: int, white_level: float) -> None:
    print(f"white block to {int(white_level * (2**bit_depth - 1))}")


pr.dispatch(CameraSettings.set_bit_depth, 8)

pr.dispatch(MonoImgSettings.set_black_level, 0.5)

pr.dispatch(CameraSettings.change_roi, (0, 0, 50, 50))

print("===========setting black level to 0.3===========")
pr.dispatch(MonoImgSettings.set_black_level, 1)
pr.dispatch(MonoImgSettings.set_black_level, 1)

print("===========setting binning===========")
pr.dispatch(CameraSettings.change_binning, (2, 2))

print("===========setting exposure===========")
pr.dispatch(CameraSettings.set_exposure, 0.2)

print("===========setting gain===========")
pr.dispatch(CameraSettings.set_bit_depth, 16)
