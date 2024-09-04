from enum import StrEnum

class StationStatus(StrEnum):
    FREE = "Free"
    WAITING = "Waiting"
    IN_PROGRESS = "In progress"

class A:
    def __init__(self) -> None:
        self.a = StationStatus.FREE

b = A()

s = []
s.append(str(b.a))

print(s)