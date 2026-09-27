"""Own the single overlay and commit Active only after its first paint."""

from PyQt6.QtCore import QObject, pyqtSignal

from .overlay import RasterOverlay
from .state import Mode, State


class DimmerController(QObject):
    changed = pyqtSignal()

    def __init__(self, preflight, create_overlay=RasterOverlay):
        super().__init__()
        self.state = State()
        self.preflight = preflight
        self.create_overlay = create_overlay
        self.overlay = None
        self.available = False
        self.message = "Checking display and emergency recovery…"

    def check_ready(self):
        if self.overlay is not None:
            return
        try:
            self.preflight()
            self.available = True
            self.message = ""
        except Exception as error:
            self.available = False
            self.message = str(error)
        self.changed.emit()

    def start(self):
        if self.overlay is not None or self.state.opacity == 0:
            return
        try:
            screen = self.preflight()
            self.available = True
            surface = self.create_overlay(screen, self.state.opacity)
            self.overlay = surface
            surface.ready.connect(lambda: self._ready(surface))
            surface.failed.connect(lambda reason: self._failed(surface, reason))
            self.message = "Starting…"
            surface.show()
        except Exception as error:
            self.available = False
            self.stop(str(error))
        self.changed.emit()

    def _ready(self, surface):
        if surface is self.overlay:
            self.state.start()
            self.message = ""
            self.changed.emit()

    def _failed(self, surface, reason):
        if surface is self.overlay:
            self.stop(reason)

    def select(self, value):
        self.state.select(value)
        if value == 0:
            self.stop()
        elif self.overlay is not None:
            try:
                self.overlay.set_opacity(value)
            except Exception as error:
                self.stop(str(error))
        self.changed.emit()

    def stop(self, reason=""):
        surface, self.overlay = self.overlay, None
        self.state.stop()
        self.message = reason
        if surface is not None:
            surface.dispose()
        self.changed.emit()

    def status(self):
        return {
            "state": self.state.mode.value,
            "opacity": self.state.opacity,
            "active": self.state.mode is Mode.ACTIVE,
            "available": self.available,
            "message": self.message,
            "paints": self.overlay.paint_count if self.overlay is not None else 0,
        }
