from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtTest import QTest

from linux_custom_dimmer.gui_controller import DimmerController
from linux_custom_dimmer.state import Mode
from linux_custom_dimmer.window import ControlWindow


class Surface(QObject):
    ready = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, screen, opacity):
        super().__init__()
        self.opacity = opacity
        self.disposed = False

    def show(self):
        self.ready.emit()

    def set_opacity(self, value):
        self.opacity = value

    def dispose(self):
        self.disposed = True


def test_controls_never_start_implicitly_and_close_removes_surface(qt_app):
    surfaces = []

    def create(screen, opacity):
        surface = Surface(screen, opacity)
        surfaces.append(surface)
        return surface

    controller = DimmerController(lambda: qt_app.primaryScreen(), create)
    window = ControlWindow(controller, lambda: None)
    window.show()
    controller.check_ready()
    assert controller.state.mode is Mode.STOPPED and window.slider.value() == 50
    window.slider.setValue(65)
    assert not surfaces
    QTest.mouseClick(window.start_button, Qt.MouseButton.LeftButton)
    assert controller.state.mode is Mode.ACTIVE and surfaces[-1].opacity == 65
    window.slider.setValue(80)
    assert surfaces[-1].opacity == 80
    window.slider.setValue(0)
    assert surfaces[-1].disposed and controller.state.mode is Mode.STOPPED
    window.slider.setValue(50)
    assert len(surfaces) == 1
    QTest.mouseClick(window.start_button, Qt.MouseButton.LeftButton)
    window.close()
    assert surfaces[-1].disposed and controller.state.mode is Mode.STOPPED


def test_missing_recovery_and_surface_failure_leave_stopped(qt_app):
    def unavailable():
        raise RuntimeError("Emergency shortcut unavailable")

    controller = DimmerController(unavailable, Surface)
    window = ControlWindow(controller, lambda: None)
    controller.check_ready()
    assert not window.start_button.isEnabled()
    assert "Emergency shortcut" in window.message.text()
    controller.start()
    assert controller.overlay is None and controller.state.mode is Mode.STOPPED
    controller.preflight = lambda: qt_app.primaryScreen()
    controller.start()
    surface = controller.overlay
    surface.failed.emit("painting failed")
    assert surface.disposed and controller.state.mode is Mode.STOPPED
    window.close()


def test_emergency_button_removes_overlay_and_quits(qt_app):
    controller = DimmerController(lambda: qt_app.primaryScreen(), Surface)
    quit_calls = []
    window = ControlWindow(controller, lambda: quit_calls.append(True))
    controller.start()
    surface = controller.overlay
    window.emergency_button.click()
    assert surface.disposed and quit_calls == [True]
    window.close()


def test_minimize_retains_state_and_relaunch_restores_controls(qt_app):
    controller = DimmerController(lambda: qt_app.primaryScreen(), Surface)
    window = ControlWindow(controller, lambda: None)
    window.show()
    controller.start()
    surface = controller.overlay
    window.showMinimized()
    assert window.isMinimized() and controller.state.mode is Mode.ACTIVE
    window.show_existing()
    assert not window.isMinimized() and controller.overlay is surface
    window.close()
    assert surface.disposed
