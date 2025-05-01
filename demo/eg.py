from __future__ import annotations

import redux as rd


class CameraSlice(rd.Slice):
    exposure: float = 0.0
    gain: float = 0.0

    # reducer can take in a payload
    @rd.reduce
    def set_exposure_s(piece: CameraSlice, exposure: float) -> CameraSlice:
        return piece.update([(CameraSlice.exposure, exposure)])

    # reducer can take no payload
    @rd.reduce
    def reset_exposure_s(piece: CameraSlice) -> CameraSlice:
        return piece.update([(CameraSlice.exposure, 0.0)])


class Store(rd.Store):
    camera: CameraSlice


rd.create_store(Store(camera=CameraSlice(exposure=0.1, gain=0.2)))

rd.dispatch(CameraSlice.set_exposure_s, 0.5)
assert rd.get_state(CameraSlice.exposure) == 0.5

rd.dispatch(CameraSlice.reset_exposure_s)
assert rd.get_state(CameraSlice.exposure) == 0.0
