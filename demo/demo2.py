
from typing import Self, TypeVar
import pyrux as pr

class MonoImgSlice(pr.Slice):
    x: int

    @pr.reduce
    def increment_x(piece: Self) -> Self:
        return piece.update([(MonoImgSlice.x, piece.x + 1)])

def subscribe_chunk(chunk: list[int]) -> None:
    @pr.subscribe(MonoImgSlice.x)
    def apply_x(value: int) -> None:
        chunk.append(value)

pr.create_store([
    MonoImgSlice(x=0),
])

chunk1 = [1]
chunk2 = [2]

subscribe_chunk(chunk1)
subscribe_chunk(chunk2)

print(chunk1)  # [1]
print(chunk2)  # [2]

pr.dispatch(MonoImgSlice.increment_x)
print(chunk1)  # [1, 1]
print(chunk2)  # [2, 1]


pr.force_notify([MonoImgSlice.x])

print(chunk1)  # [1, 1, 1]
print(chunk2)  # [2, 1, 1]

pr.dispatch_state(MonoImgSlice.x, "121")

print(chunk1)  # [1, 1, 1, 121]
print(chunk2)  # [2, 1, 121]

