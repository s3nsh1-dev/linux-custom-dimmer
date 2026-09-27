"""Explicit opt-in: disposable services and sentinel only; no Qt or display changes."""

import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pytest

from linux_custom_dimmer.control import Controller, Identity, RecoveryError
from linux_custom_dimmer.service import Systemd

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("DIMMER_LIVE_TESTS") != "1", reason="set DIMMER_LIVE_TESTS=1 explicitly"
    ),
]
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DummyIdentity(Identity):
    @property
    def argv(self):
        return ["/usr/bin/python3", "-I", str(ROOT / "tests/integration/dummy.py"), "--freeze"]


def controller(identity):
    return Controller(identity, Path(os.environ["XDG_RUNTIME_DIR"]), Systemd())


def wait_for(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for disposable test process")


def process_identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split(")", 1)[1].split()
        return fields[0], fields[19]
    except FileNotFoundError:
        return None


@pytest.mark.parametrize("action,limit", [("stop", 3), ("kill", 1)])
def test_frozen_service_recovery_and_unrelated_sentinel(action, limit):
    identity = DummyIdentity(ROOT, f"linux-custom-dimmer-test-{os.getpid()}.service")
    ctl = controller(identity)
    sentinel = subprocess.Popen(["/usr/bin/sleep", "30"])
    sentinel_start = process_identity(sentinel.pid)[1]
    try:
        ctl.perform("launch", runtime_limit=10)

        def frozen():
            with ctl.backend.pinned(identity.unit) as props:
                if props and props["MainPID"]:
                    pid = int(props["MainPID"])
                    state = process_identity(pid)
                    if state and state[0] == "T":
                        return pid
            return None

        pid = wait_for(frozen)
        children = [
            int(value) for value in Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
        ]
        assert children
        started = time.monotonic()
        # A separate Python process runs exactly the production recovery implementation.
        code = (
            "from tests.integration.test_recovery import controller, DummyIdentity, ROOT; "
            f"print(controller(DummyIdentity(ROOT, {identity.unit!r})).perform({action!r}))"
        )
        result = subprocess.run(
            [str(ROOT / ".venv/bin/python3"), "-c", code],
            env={**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}"},
            capture_output=True,
            text=True,
            timeout=6,
        )
        assert result.returncode == 0, result.stderr
        elapsed = time.monotonic() - started
        assert elapsed < limit
        for owned_pid in [pid, *children]:
            wait_for(
                lambda p=owned_pid: process_identity(p) is None or process_identity(p)[0] == "Z"
            )
        assert sentinel.poll() is None
        assert process_identity(sentinel.pid)[1] == sentinel_start
        print(f"{action}: {elapsed:.3f}s, frozen parent/child removed, sentinel survived")
    finally:
        ctl.perform("kill")
        sentinel.terminate()
        sentinel.wait(timeout=3)


def test_concurrent_launch_and_real_unit_collision():
    identity = DummyIdentity(ROOT, f"linux-custom-dimmer-race-{os.getpid()}.service")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda _: controller(identity).perform("launch", runtime_limit=8), range(2)
                )
            )
        assert sorted(results) == ["Already running", "Launched"]
        foreign = DummyIdentity(ROOT / "different project", identity.unit)
        for action in ["launch", "stop", "kill"]:
            with pytest.raises(RecoveryError, match="identity"):
                controller(foreign).perform(action)
        with controller(identity).backend.pinned(identity.unit) as props:
            assert props["ActiveState"] == "active"
    finally:
        controller(identity).perform("kill")


def test_manager_deadline_expires_even_when_dummy_is_frozen():
    identity = DummyIdentity(ROOT, f"linux-custom-dimmer-deadline-{os.getpid()}.service")
    ctl = controller(identity)
    try:
        ctl.perform("launch", runtime_limit=1)

        def absent():
            with ctl.backend.pinned(identity.unit) as props:
                return props is None or props["ActiveState"] in {"inactive", "failed"}

        wait_for(absent, timeout=5)
    finally:
        ctl.perform("kill")
