"""One normal control window and at most one caller-owned dimming window."""

import os
import signal
import socket
import sys
from pathlib import Path

from PyQt6.QtCore import QSocketNotifier, QTimer
from PyQt6.QtWidgets import QApplication

from .control import Controller, Identity, RecoveryError
from .gui_controller import DimmerController
from .integration import Integration
from .local_server import LocalServer
from .native import NativeBridge
from .service import Systemd
from .session import SessionGuard, builtin_screen
from .support import check_session
from .window import ControlWindow


class SignalWakeup:
    """Wake Qt for SIGTERM/SIGINT without an idle polling timer."""

    def __init__(self, quit_app):
        self.reader, self.writer = socket.socketpair()
        self.reader.setblocking(False)
        self.writer.setblocking(False)
        self.old_fd = signal.set_wakeup_fd(self.writer.fileno())
        self.old_handlers = {}
        for sig in (signal.SIGTERM, signal.SIGINT):
            self.old_handlers[sig] = signal.signal(sig, lambda *_: None)
        self.notifier = QSocketNotifier(self.reader.fileno(), QSocketNotifier.Type.Read)
        self.notifier.activated.connect(lambda *_: self.wake(quit_app))

    def wake(self, quit_app):
        self.reader.recv(1024)
        quit_app()

    def close(self):
        self.notifier.setEnabled(False)
        signal.set_wakeup_fd(self.old_fd)
        for sig, handler in self.old_handlers.items():
            signal.signal(sig, handler)
        self.reader.close()
        self.writer.close()


def main():
    os.umask(0o077)
    root = Path(__file__).resolve().parents[2]
    app = QApplication(sys.argv)
    app.setApplicationName("Linux Custom Dimmer")
    app.setDesktopFileName("linux-custom-dimmer")
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    owner = Controller(Identity(root), runtime, Systemd())

    def verify_service():
        with owner.backend.pinned(owner.identity.unit) as properties:
            if properties is None:
                raise RecoveryError("Launch this app using bin/dimmer")
            owner.verify(properties)
            if int(properties.get("MainPID", 0)) != os.getpid():
                raise RecoveryError("This process is not the owned dimmer service")
            return properties

    service_properties = verify_service()
    # Explicit test launches have an outer manager deadline and this separate
    # cooperative timer. Normal launches have RuntimeMaxUSec=infinity and no timer.
    runtime_usec = int(service_properties.get("RuntimeMaxUSec", 0))
    if 0 < runtime_usec <= 900_000_000:
        QTimer.singleShot(max(1, runtime_usec // 1000 - 250), app.quit)
    guard = SessionGuard(app)
    monitor_error = ""
    try:
        guard.connect_dbus()
    except Exception as error:
        monitor_error = str(error)

    def preflight():
        if monitor_error:
            raise RuntimeError(monitor_error)
        guard.ensure_unlocked()
        check_session()
        verify_service()
        Integration(root).verify()
        NativeBridge()
        return builtin_screen(app.screens())

    controller = DimmerController(preflight)
    window = ControlWindow(controller, app.quit)
    guard.unsafe.connect(controller.stop)

    def dispatch(payload):
        action = payload["action"]
        if action == "show":
            window.show_existing()
        elif action == "start":
            controller.start()
        elif action == "stop":
            controller.stop()
        elif action == "select":
            controller.select(payload["value"])
        elif action == "quit":
            controller.stop()
            QTimer.singleShot(0, app.quit)
        return controller.status()

    server = LocalServer(owner.directory / "control.sock", dispatch)
    wakeup = SignalWakeup(app.quit)
    app.aboutToQuit.connect(lambda: controller.stop())
    window.show()
    QTimer.singleShot(0, controller.check_ready)
    previous_hook = sys.excepthook

    def fail_closed(kind, value, traceback):
        controller.stop("Unexpected error; dimming stopped")
        previous_hook(kind, value, traceback)
        app.quit()

    sys.excepthook = fail_closed
    try:
        return app.exec()
    finally:
        controller.stop()
        server.close()
        wakeup.close()
        sys.excepthook = previous_hook
