import pytest
from PyQt6.QtCore import QObject, pyqtSignal

from linux_custom_dimmer.session import SessionGuard, builtin_screen
from linux_custom_dimmer.state import Mode
from tests.test_window import DimmerController, Surface


class Screens(QObject):
    screenAdded = pyqtSignal(object)
    screenRemoved = pyqtSignal(object)

    def screens(self):
        return []


@pytest.mark.parametrize("event", ["lock", "sleep", "topology", "disconnect"])
def test_session_changes_stop_and_never_restart(qt_app, event):
    ctl = DimmerController(lambda: qt_app.primaryScreen(), Surface)
    guard = SessionGuard(Screens())
    guard.unsafe.connect(ctl.stop)
    ctl.start()
    surface = ctl.overlay
    if event == "lock":
        guard.lock_changed(True)
        guard.lock_changed(False)
    elif event == "sleep":
        guard.sleep_changed(True)
        guard.sleep_changed(False)
    elif event == "topology":
        guard.topology_changed()
    else:
        guard.connection_lost()
    assert surface.disposed and ctl.state.mode is Mode.STOPPED
    assert ctl.overlay is None


def test_builtin_connector_discovery_refuses_external_only_or_ambiguous():
    class Screen:
        def __init__(self, name):
            self.value = name

        def name(self):
            return self.value

    laptop = Screen("eDP-2")
    assert builtin_screen([Screen("HDMI-A-1"), laptop]) is laptop
    for screens in [[], [Screen("HDMI-A-1")], [laptop, Screen("eDP-1")]]:
        with pytest.raises(RuntimeError):
            builtin_screen(screens)
