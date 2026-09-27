"""Temporarily register only our own no-key command; exercise KDE's launcher."""

import os
import subprocess
import time
from pathlib import Path

import dbus
import pytest

from tests.integration.test_recovery import (
    ROOT,
    DummyIdentity,
    controller,
    process_identity,
    wait_for,
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("DIMMER_KDE_TESTS") != "1", reason="set DIMMER_KDE_TESTS=1 explicitly"
    ),
]


def desktop_quote(value):
    return (
        '"'
        + str(value)
        .replace("\\", "\\\\\\\\")
        .replace('"', '\\\\"')
        .replace("`", "\\\\`")
        .replace("$", "\\\\$")
        .replace("%", "%%")
        + '"'
    )


def test_kde_launches_independent_recovery_for_frozen_dummy():
    component = "linux-custom-dimmer-stage1-probe.desktop"
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    desktop = data / "kglobalaccel" / component
    desktop.parent.mkdir(parents=True, exist_ok=True)
    # Refuse a collision rather than overwriting even an old test file.
    with desktop.open("x") as stream:
        stream.write(
            "[Desktop Entry]\nType=Application\nName=Dimmer Stage 1 recovery probe\n"
            f"Exec={desktop_quote(ROOT / '.venv/bin/python3')} -I "
            f"{desktop_quote(ROOT / 'tests/integration/kde_recovery.py')}\n"
            "StartupNotify=false\nX-KDE-GlobalAccel-CommandShortcut=true\nX-KDE-Shortcuts=none\n"
        )
    bus = dbus.SessionBus()
    service = "org.kde.kglobalaccel"
    manager = dbus.Interface(bus.get_object(service, "/kglobalaccel"), "org.kde.KGlobalAccel")
    identity = DummyIdentity(ROOT, "linux-custom-dimmer-kde-probe.service")
    ctl = controller(identity)
    sentinel = subprocess.Popen(["/usr/bin/sleep", "30"])
    sentinel_start = process_identity(sentinel.pid)[1]
    try:
        subprocess.run(["desktop-file-validate", str(desktop)], check=True)
        available = bool(manager.isGlobalShortcutAvailable(234881092, component))
        print(f"Ctrl+Alt+Shift+D available: {available}; probe binds no key")
        manager.doRegister([component, "_launch", "Dimmer probe", "Recover dummy"])
        path = manager.getComponent(component)
        route = dbus.Interface(bus.get_object(service, path), service + ".Component")
        assert "_launch" in route.shortcutNames()
        ctl.perform("launch", runtime_limit=10)

        def frozen():
            with ctl.backend.pinned(identity.unit) as props:
                if props and props["MainPID"]:
                    pid = int(props["MainPID"])
                    info = process_identity(pid)
                    if info and info[0] == "T":
                        return pid
            return None

        pid = wait_for(frozen)
        started = time.monotonic()
        route.invokeShortcut("_launch")
        wait_for(lambda: process_identity(pid) is None or process_identity(pid)[0] == "Z")
        elapsed = time.monotonic() - started
        assert elapsed < 1
        assert sentinel.poll() is None and process_identity(sentinel.pid)[1] == sentinel_start
        print(f"KDE external command killed frozen dummy in {elapsed:.3f}s; sentinel survived")
    finally:
        ctl.perform("kill")
        sentinel.terminate()
        sentinel.wait(timeout=3)
        manager.unregister(component, "_launch")
        desktop.unlink()
        subprocess.run(
            ["kbuildsycoca6", "--noincremental"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
