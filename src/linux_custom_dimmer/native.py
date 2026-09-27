"""Lifetime-checked bridge loading, separate from painting and session detection."""

import ctypes
from pathlib import Path

from PyQt6 import sip
from PyQt6.QtCore import QThread, qVersion
from PyQt6.QtGui import QGuiApplication, QWindow


class NativeError(RuntimeError):
    pass


class NativeBridge:
    def __init__(self, path=None):
        self.path = path or (
            Path(__file__).resolve().parents[2] / "build/native/libdimmer_layer_shell.so"
        )
        try:
            # Keep the GIL throughout native access to the borrowed Qt object.
            self.library = ctypes.PyDLL(str(self.path))
            self.library.dimmer_bridge_abi.restype = ctypes.c_int
            self.library.dimmer_build_qt.restype = ctypes.c_char_p
            self.library.dimmer_runtime_qt.restype = ctypes.c_char_p
            self.library.dimmer_configure.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            self.library.dimmer_configure.restype = ctypes.c_int
            if self.library.dimmer_bridge_abi() != 1:
                raise NativeError("Unsupported native adapter ABI; rebuild with scripts/setup-dev")
            versions = (self.library.dimmer_build_qt(), self.library.dimmer_runtime_qt())
            if any(version != qVersion().encode() for version in versions):
                raise NativeError("Qt version mismatch; rebuild with scripts/setup-dev")
        except (OSError, AttributeError) as error:
            raise NativeError("Native adapter unavailable; build with scripts/setup-dev") from error

    def configure(self, window):
        app = QGuiApplication.instance()
        if app is None or QThread.currentThread() != app.thread():
            raise NativeError("Configure the overlay on the GUI thread with a QGuiApplication")
        if not isinstance(window, QWindow) or sip.isdeleted(window):
            raise NativeError("Native adapter requires a live QWindow")
        code = self.library.dimmer_configure(sip.unwrapinstance(window), qVersion().encode())
        messages = {
            1: "QGuiApplication is required",
            2: "Configure the window on the GUI thread",
            3: "Qt version mismatch",
            4: "A live QWindow is required",
            5: "Wayland Qt platform is required",
            6: "Configure before creating the surface",
            7: "Layer-shell configuration failed; destroy the caller-owned window",
        }
        if code:
            raise NativeError(messages.get(code, f"Native adapter error {code}"))
