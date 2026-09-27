"""One input-transparent raster window, painted only on exposure or change."""

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QBackingStore, QColor, QPainter, QRegion, QSurfaceFormat, QWindow

from .native import NativeBridge


def validate_opacity(value):
    if type(value) is not int or not 1 <= value <= 80:
        raise ValueError("Visible overlay opacity must be an integer from 1 to 80")


class RasterOverlay(QWindow):
    ready = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, screen, opacity, bridge=None):
        validate_opacity(opacity)
        super().__init__(screen)
        self.opacity_value = opacity
        self.paint_count = 0
        self.closed = False
        self.backing = None
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(
            lambda: self.failed.emit("Display did not expose the overlay")
        )
        try:
            surface = QSurfaceFormat()
            surface.setAlphaBufferSize(8)
            self.setFormat(surface)
            self.setTitle("Linux Custom Dimmer overlay")
            self.setGeometry(screen.geometry())
            (bridge or NativeBridge()).configure(self)
            self.backing = QBackingStore(self)
        except Exception:
            sip.delete(self)
            raise

    def show(self):
        self.deadline.start(1500)
        super().show()

    def set_opacity(self, opacity):
        validate_opacity(opacity)
        if opacity != self.opacity_value and not self.closed:
            self.opacity_value = opacity
            self.requestUpdate()

    def event(self, event):
        if event.type() == QEvent.Type.UpdateRequest:
            self.paint()
            return True
        if event.type() == QEvent.Type.Close and not self.closed:
            self.failed.emit("Display closed the overlay; press Start to resume")
            return True
        return super().event(event)

    def exposeEvent(self, event):
        self.paint()

    def resizeEvent(self, event):
        if self.backing is not None and not self.closed:
            self.requestUpdate()

    def paint(self):
        if self.closed or self.backing is None or not self.isExposed():
            return
        try:
            self.backing.resize(self.size())
            rect = QRect(0, 0, self.width(), self.height())
            region = QRegion(rect)
            self.backing.beginPaint(region)
            painter = QPainter(self.backing.paintDevice())
            try:
                # Replace every pixel; SourceOver would accumulate darkness on repaint.
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.fillRect(rect, QColor(0, 0, 0, round(self.opacity_value * 255 / 100)))
            finally:
                painter.end()
                self.backing.endPaint()
            self.backing.flush(region)
            self.paint_count += 1
            if self.paint_count == 1:
                self.deadline.stop()
                self.ready.emit()
        except Exception as error:
            self.failed.emit(f"Could not paint overlay: {error}")

    def dispose(self):
        if self.closed:
            return
        self.closed = True
        self.deadline.stop()
        self.hide()
        if self.backing is not None:
            sip.delete(self.backing)
            self.backing = None
        self.destroy()
        self.deleteLater()
