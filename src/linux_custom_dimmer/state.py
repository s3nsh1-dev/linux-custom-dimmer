"""Pure selection/state contract; starting here never creates a window."""

from enum import Enum


class Mode(Enum):
    STOPPED = "Stopped"
    ACTIVE = "Active"


class State:
    def __init__(self):
        self._opacity = 50
        self._mode = Mode.STOPPED

    @property
    def opacity(self):
        return self._opacity

    @property
    def mode(self):
        return self._mode

    @property
    def effective_opacity(self):
        return self._opacity if self._mode is Mode.ACTIVE else 0

    def select(self, value):
        if type(value) is not int or not 0 <= value <= 80:
            raise ValueError("Extra dimming must be an integer from 0 to 80")
        self._opacity = value
        if value == 0:
            self.stop()

    def start(self):
        self._mode = Mode.ACTIVE if self._opacity else Mode.STOPPED

    def stop(self):
        self._mode = Mode.STOPPED
