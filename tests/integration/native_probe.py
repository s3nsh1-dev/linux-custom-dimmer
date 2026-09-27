"""Unmapped Wayland windows only. Outer service deadline is required by the runner."""

import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QGuiApplication, QSurfaceFormat, QWindow

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from linux_custom_dimmer.native import NativeBridge, NativeError  # noqa: E402
from linux_custom_dimmer.support import check_session  # noqa: E402

check_session()
app = QGuiApplication([])
bridge = NativeBridge()
normal = QWindow()
normal.setTitle("Unmapped normal-window probe")
normal.create()
overlay = QWindow()
surface = QSurfaceFormat()
surface.setAlphaBufferSize(8)
overlay.setFormat(surface)
bridge.configure(overlay)
overlay.create()
try:
    bridge.configure(overlay)
except NativeError as error:
    assert "before creating" in str(error)
else:
    raise AssertionError("Already-created surface was accepted")
assert not overlay.isVisible() and not normal.isVisible()
print("native probe: configured caller-owned window; both windows remain unmapped", flush=True)
QTimer.singleShot(250, app.quit)
app.exec()
overlay.destroy()
normal.destroy()
