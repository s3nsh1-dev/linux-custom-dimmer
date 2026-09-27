import copy
import os
from contextlib import contextmanager
from pathlib import Path

import pytest

from linux_custom_dimmer.control import Controller, Identity, RecoveryError, parse_action


class FakeManager:
    """External systemd boundary only. No real services in the default suite."""

    def __init__(self):
        self.unit = None
        self.calls = []

    @contextmanager
    def pinned(self, name):
        yield self.unit

    def start(self, identity, token, environment, runtime_limit=None):
        self.calls.append(("start", identity.unit, identity.argv))
        self.unit = {
            "Transient": True,
            "Description": identity.description,
            "ExecStart": [(identity.argv[0], identity.argv, False)],
            "Environment": [f"LINUX_CUSTOM_DIMMER_OWNER={token}"],
            "ActiveState": "active",
            "KillMode": "control-group",
            "Restart": "no",
            "TimeoutStopUSec": 2000000,
            "SendSIGKILL": True,
        }

    def stop(self, unit, immediate):
        self.calls.append(("kill" if immediate else "stop", unit))
        self.unit = None


@pytest.fixture
def fixture(tmp_path):
    identity = Identity(tmp_path / "project with spaces", "linux-custom-dimmer-test.service")
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    backend = FakeManager()
    return Controller(identity, runtime, backend), backend


def test_missing_stop_is_harmless_and_launches_do_not_stack(fixture):
    control, backend = fixture
    assert control.perform("stop") == "Already stopped"
    assert control.perform("kill") == "Already stopped"
    assert backend.calls == []
    control.perform("launch")
    assert control.perform("launch") == "Already running"
    assert [call[0] for call in backend.calls] == ["start"]
    assert backend.calls[0][2][0].endswith("project with spaces/.venv/bin/python3")
    assert backend.calls[0][2][1] == "-I"
    control.perform("kill")
    assert backend.calls[-1] == ("kill", "linux-custom-dimmer-test.service")


@pytest.mark.parametrize(
    "field,value",
    [
        ("Transient", False),
        ("Description", "unrelated"),
        ("ExecStart", [("/usr/bin/python3", ["/usr/bin/python3", "other.py"], False)]),
        ("Environment", ["LINUX_CUSTOM_DIMMER_OWNER=stale"]),
        ("KillMode", "process"),
        ("Restart", "always"),
        ("TimeoutStopUSec", 90000000),
        ("SendSIGKILL", False),
    ],
)
@pytest.mark.parametrize("action", ["launch", "stop", "kill"])
def test_collision_or_stale_record_never_signals_a_service(fixture, field, value, action):
    control, backend = fixture
    control.perform("launch")
    backend.unit[field] = value
    before = copy.deepcopy(backend.calls)
    with pytest.raises(RecoveryError, match="identity"):
        control.perform(action)
    assert backend.calls == before


def test_absent_ownership_record_does_not_adopt_live_unit(fixture):
    control, backend = fixture
    control.perform("launch")
    control.record_path.unlink()
    with pytest.raises(RecoveryError):
        control.perform("kill")
    assert len(backend.calls) == 1


@pytest.mark.parametrize("bad_path", ["symlink", "public"])
def test_runtime_record_must_be_private(fixture, tmp_path, bad_path):
    control, backend = fixture
    control.perform("launch")
    if bad_path == "symlink":
        target = tmp_path / "other"
        control.record_path.rename(target)
        control.record_path.symlink_to(target)
    else:
        os.chmod(control.record_path, 0o644)
    with pytest.raises(RecoveryError):
        control.perform("kill")
    assert len(backend.calls) == 1


@pytest.mark.parametrize(
    "args",
    [
        ["--unit", "kwin.service"],
        ["--kill", "123"],
        ["--stop", "--kill"],
        ["--opacity", "nan"],
        ["--kil"],
    ],
)
def test_cli_rejects_arbitrary_targets_and_malformed_input(args):
    with pytest.raises(SystemExit) as exc:
        parse_action(args)
    assert exc.value.code == 2


def test_cli_has_only_fixed_actions():
    assert parse_action([]) == "launch"
    assert parse_action(["--stop"]) == "stop"
    assert parse_action(["--kill"]) == "kill"


@pytest.mark.parametrize("state", ["inactive", "failed", "deactivating"])
def test_loaded_but_not_running_unit_requests_retry_without_restarting(fixture, state):
    control, backend = fixture
    control.perform("launch")
    backend.unit["ActiveState"] = state
    with pytest.raises(RecoveryError, match="retry"):
        control.perform("launch")
    assert len(backend.calls) == 1


def test_control_does_not_import_qt():
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import linux_custom_dimmer.control; "
            "assert not any(x.startswith('PyQt6') for x in sys.modules)",
        ],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
