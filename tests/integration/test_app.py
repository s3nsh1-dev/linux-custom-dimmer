"""Opt-in real application tests: short deadlines, verified signals, no user input."""

import os
import signal
import subprocess
import time

import dbus
import pytest

from linux_custom_dimmer.control import Identity
from linux_custom_dimmer.integration import COMPONENT, Integration
from linux_custom_dimmer.ipc import request
from linux_custom_dimmer.service import UNIT
from tests.integration.resources import sentinel_process
from tests.integration.test_recovery import ROOT, controller, process_identity, wait_for

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("DIMMER_APP_TESTS") != "1", reason="explicit live opt-in"),
]


@pytest.fixture
def app():
    ctl = controller(Identity(ROOT))
    with ctl.backend.pinned(ctl.identity.unit) as props:
        assert props is None, "Close the existing dimmer before live tests"
    ctl.perform("launch", runtime_limit=15)
    try:

        def ready():
            try:
                return request(ctl.directory / "control.sock", {"action": "status"})["status"]
            except OSError:
                return None

        status = wait_for(ready)
        assert status["state"] == "Stopped" and status["available"], status
        yield ctl
    finally:
        ctl.perform("kill")
        wait_for(lambda: absent(ctl))


def call(ctl, action, **kwargs):
    return request(ctl.directory / "control.sock", {"action": action, **kwargs})["status"]


def absent(ctl):
    with ctl.backend.pinned(ctl.identity.unit) as props:
        return props is None


def owned_signal(ctl, signum):
    with ctl.locked(), ctl.backend.pinned(ctl.identity.unit) as props:
        ctl.verify(props)
        pid = int(props["MainPID"])
        # The pinned, verified service is the signal target; never search names/PIDs.
        dbus.Interface(ctl.backend.objects[ctl.identity.unit], UNIT).Kill("main", signum)
        return pid


def test_relaunch_cannot_stack_and_zero_stop_removes_layer(app):
    with app.backend.pinned(app.identity.unit) as props:
        pid = int(props["MainPID"])
    call(app, "start")
    wait_for(lambda: call(app, "status")["active"])
    for _ in range(2):
        result = subprocess.run([ROOT / "bin/dimmer"], capture_output=True, text=True, timeout=5)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "Already running"
    with app.backend.pinned(app.identity.unit) as props:
        assert int(props["MainPID"]) == pid
    before = call(app, "status")
    time.sleep(0.3)
    assert call(app, "status")["paints"] == before["paints"]
    call(app, "select", value=0)
    assert not call(app, "status")["active"]
    call(app, "select", value=65)
    assert not call(app, "status")["active"]
    call(app, "start")
    wait_for(lambda: call(app, "status")["active"])
    call(app, "stop")
    assert call(app, "status")["state"] == "Stopped"


@pytest.mark.parametrize("route", ["shortcut", "menu", "stop"])
def test_installed_recovery_removes_frozen_real_app_only(app, route):
    with sentinel_process() as sentinel:
        identity = process_identity(sentinel.pid)
        call(app, "start")
        wait_for(lambda: call(app, "status")["active"])
        pid = owned_signal(app, signal.SIGSTOP)
        wait_for(lambda: process_identity(pid)[0] == "T")
        started = time.monotonic()
        if route == "shortcut":
            integration = Integration(ROOT)
            integration.verify()
            manager = integration.shortcuts.manager
            path = manager.getComponent(COMPONENT)
            component = dbus.Interface(
                integration.shortcuts.bus.get_object("org.kde.kglobalaccel", path),
                "org.kde.kglobalaccel.Component",
            )
            component.invokeShortcut("_launch")
        elif route == "menu":
            desktop = next(p for p in Integration(ROOT).entries() if p.name == COMPONENT)
            subprocess.run(["/usr/bin/kioclient", "exec", str(desktop)], check=True, timeout=5)
        else:
            subprocess.run([ROOT / "bin/dimmer", "--stop"], check=True, timeout=5)
        wait_for(lambda: process_identity(pid) is None)
        elapsed = time.monotonic() - started
        assert elapsed < (3 if route == "stop" else 1), elapsed
        assert sentinel.poll() is None and process_identity(sentinel.pid)[1] == identity[1]
        print(f"frozen app {route}: {elapsed:.3f}s; sentinel survived", flush=True)


@pytest.mark.parametrize("exit_method", ["quit", signal.SIGTERM, signal.SIGKILL])
def test_exit_paths_remove_real_app(app, exit_method):
    call(app, "start")
    wait_for(lambda: call(app, "status")["active"])
    if exit_method == "quit":
        call(app, "quit")
    else:
        owned_signal(app, exit_method)
    wait_for(lambda: absent(app))
