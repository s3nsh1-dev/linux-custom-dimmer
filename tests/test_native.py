import os
import subprocess
import threading
from pathlib import Path

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6 import sip
from PyQt6.QtGui import QGuiApplication, QWindow

from linux_custom_dimmer.native import NativeBridge, NativeError
from linux_custom_dimmer.support import SupportError, check_session


@pytest.fixture(scope="module")
def app():
    instance = QGuiApplication.instance() or QGuiApplication([])
    yield instance


def test_missing_library_fails_before_any_surface(tmp_path):
    with pytest.raises(NativeError, match="build"):
        NativeBridge(tmp_path / "missing.so")


def test_wrong_qt_version_refused_before_configuring(app):
    bridge = NativeBridge()
    assert bridge.library.dimmer_configure(None, b"0.0.0") == 3


def test_offscreen_and_deleted_window_are_refused(app):
    bridge = NativeBridge()
    window = QWindow()
    with pytest.raises(NativeError, match="Wayland"):
        bridge.configure(window)
    assert not window.isVisible()
    sip.delete(window)
    with pytest.raises(NativeError, match="live QWindow"):
        bridge.configure(window)


def test_wrong_thread_is_refused_before_accessing_window(app):
    bridge = NativeBridge()
    window = QWindow()
    errors = []

    def configure():
        try:
            bridge.configure(window)
        except NativeError as error:
            errors.append(str(error))

    thread = threading.Thread(target=configure)
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert errors and "GUI thread" in errors[0]
    assert not window.isVisible()


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"XDG_SESSION_TYPE": "x11", "XDG_CURRENT_DESKTOP": "KDE"},
        {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME"},
        {
            "XDG_SESSION_TYPE": "wayland",
            "XDG_CURRENT_DESKTOP": "KDE",
            "WAYLAND_DISPLAY": "wayland-0",
            "QT_WAYLAND_SHELL_INTEGRATION": "layer-shell",
        },
    ],
)
def test_unsupported_environment_does_not_query_or_create_windows(env):
    def forbidden(*args, **kwargs):
        pytest.fail("unsupported session queried Wayland")

    with pytest.raises(SupportError):
        check_session(env, forbidden)


@pytest.mark.parametrize("output", ["", "interface: 'xdg_wm_base', version: 6, name: 2"])
def test_missing_protocol_fails_closed(output):
    env = {
        "XDG_SESSION_TYPE": "wayland",
        "XDG_CURRENT_DESKTOP": "KDE",
        "WAYLAND_DISPLAY": "wayland-0",
    }
    with pytest.raises(SupportError, match="layer-shell"):
        check_session(env, lambda *a, **k: subprocess.CompletedProcess(a, 0, output, ""))


def test_wayland_query_has_deadline_and_uses_no_shell():
    env = {
        "XDG_SESSION_TYPE": "wayland",
        "XDG_CURRENT_DESKTOP": "KDE",
        "WAYLAND_DISPLAY": "wayland-0",
    }

    def timed_out(args, **kwargs):
        assert args == ["/usr/bin/wayland-info"]
        assert kwargs["timeout"] <= 2
        assert not kwargs.get("shell", False)
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    with pytest.raises(SupportError):
        check_session(env, timed_out)


def test_supported_protocol_accepts_wayland_info_column_spacing():
    env = {
        "XDG_SESSION_TYPE": "wayland",
        "XDG_CURRENT_DESKTOP": "KDE",
        "WAYLAND_DISPLAY": "wayland-0",
    }
    output = "interface: 'zwlr_layer_shell_v1',                        version:  5, name: 61\n"
    check_session(env, lambda *a, **k: subprocess.CompletedProcess(a, 0, output, ""))


def test_adapter_is_a_local_build():
    assert Path(NativeBridge().path).resolve().parent.name == "native"
