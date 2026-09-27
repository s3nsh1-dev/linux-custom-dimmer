"""Short real-app probe using its fixed service, preflight, socket and recovery."""

import os
import time
from pathlib import Path

from linux_custom_dimmer.control import Controller, Identity
from linux_custom_dimmer.ipc import request
from linux_custom_dimmer.service import Systemd

root = Path(__file__).resolve().parents[2]
controller = Controller(Identity(root), Path(os.environ["XDG_RUNTIME_DIR"]), Systemd())
with controller.backend.pinned(controller.identity.unit) as existing:
    if existing is not None:
        raise RuntimeError("Close the existing dimmer before the app probe")
controller.perform("launch", runtime_limit=20)
path = controller.directory / "control.sock"


def call(action, **kwargs):
    return request(path, {"action": action, **kwargs})["status"]


try:
    deadline = time.monotonic() + 5
    while True:
        try:
            status = call("status")
            break
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)
    print("launch:", status, flush=True)
    assert status["state"] == "Stopped" and status["opacity"] == 50
    assert status["available"], status["message"]
    for opacity in [50, 65, 80]:
        call("select", value=opacity)
        call("start")
        time.sleep(0.6)
        before = call("status")
        assert before["active"], before
        time.sleep(0.6)
        after = call("status")
        assert after["paints"] == before["paints"], (before, after)
        print("active, then idle:", after, flush=True)
    call("select", value=0)
    assert call("status")["state"] == "Stopped"
    print("zero removed overlay", flush=True)
finally:
    print(controller.perform("kill"), flush=True)
