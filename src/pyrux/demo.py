from __future__ import annotations
from typing import Literal
from pyrux.py_api import Slice, immer, reduce, extra_reduce
from pyrux import store


class CameraSlice(Slice):
    exposure: float
    gain: float
    binning: int
    bit_depth: Literal[8, 16]
    readout_speed: int
    model: str

    @reduce
    def change_exposure(piece: CameraSlice, payload: float) -> CameraSlice:
        return immer(piece, {CameraSlice.exposure: payload})

    @reduce
    def increment_exposure(piece: CameraSlice) -> CameraSlice:
        return immer(piece, {CameraSlice.exposure: piece.exposure + 1})

    @reduce
    def change_bit_depth(piece: CameraSlice, payload: Literal[8, 16]) -> CameraSlice:
        return immer(piece, {CameraSlice.bit_depth: payload})


class ImgSlice(Slice):
    width: int
    height: int
    pixel_size: float
    white_level: float
    black_level: float

    @reduce
    def change_white_level(piece: ImgSlice, payload: float) -> ImgSlice:
        if payload >= piece.black_level:
            return immer(piece, {ImgSlice.white_level: payload})
        else:
            return immer(
                piece,
                {
                    ImgSlice.white_level: piece.black_level,
                    ImgSlice.black_level: piece.black_level,
                },
            )

    @reduce
    def change_black_level(piece: ImgSlice, payload: float) -> ImgSlice:
        if payload <= piece.white_level:
            return immer(piece, {ImgSlice.black_level: payload})
        else:
            return immer(
                piece,
                {
                    ImgSlice.black_level: piece.white_level,
                    ImgSlice.white_level: piece.white_level,
                },
            )

    @extra_reduce(CameraSlice.binning)
    def react_to_binning(piece: ImgSlice, state: int) -> ImgSlice:
        return immer(piece, {ImgSlice.black_level: piece.black_level / state})

store.create_store(
    [
        CameraSlice(
            exposure=0.01,
            gain=1.0,
            bit_depth=8,
            binning=1,
            readout_speed=1,
            model="ModelX",
        ),
        ImgSlice(
            width=1920,
            height=1080,
            pixel_size=1.0,
            white_level=0.6,
            black_level=0.2,
        ),
    ]
)


@store.subscribe((ImgSlice.black_level, ImgSlice.white_level, CameraSlice.bit_depth))
def show_levels(args: tuple[float, float, int]) -> None:
    mag: int = 2 ** (args[2] - 1)
    print(f"White level: {args[0] * mag}, Black level: {args[1] * mag}")

print("===========setting black level to 0.3===========")
store.dispatch(ImgSlice.change_black_level, 0.3)
print("===========setting black level to 0.7===========")
store.dispatch(ImgSlice.change_black_level, 0.7)
print("===========setting white level to 0.4===========")
store.dispatch(ImgSlice.change_white_level, 0.9)
print("===========change_bit_depth to 16===========")
store.dispatch(CameraSlice.change_bit_depth, 16)

print(store.get_store())

