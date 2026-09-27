"""Independent, fixed-target service control. This module never imports Qt."""

import argparse
import fcntl
import hashlib
import json
import os
import secrets
import stat
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


class RecoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class Identity:
    root: Path
    unit: str = "linux-custom-dimmer.service"

    @property
    def argv(self):
        return [str(self.root / ".venv/bin/python3"), "-I", str(self.root / "libexec/dimmer-app")]

    @property
    def description(self):
        digest = hashlib.sha256(str(self.root).encode()).hexdigest()[:24]
        return f"Linux Custom Dimmer [{digest}]"


def private_directory(path):
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RecoveryError(f"Runtime directory must be owned by this user and mode 0700: {path}")


def private_file(path, flags):
    try:
        fd = os.open(path, flags | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    except OSError as error:
        raise RecoveryError(f"Cannot safely open runtime file: {path}") from error
    info = os.fstat(fd)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
        or info.st_nlink != 1
    ):
        os.close(fd)
        raise RecoveryError(f"Runtime file must be private and owned by this user: {path}")
    return fd


class Controller:
    def __init__(self, identity, runtime, backend):
        self.identity = identity
        self.backend = backend
        private_directory(runtime)
        self.directory = runtime / identity.unit.removesuffix(".service")
        private_directory(self.directory)
        self.record_path = self.directory / "owner.json"

    @contextmanager
    def locked(self):
        fd = private_file(self.directory / "control.lock", os.O_CREAT | os.O_RDWR)
        try:
            deadline = time.monotonic() + 1
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise RecoveryError("Another launcher is busy; retry recovery") from None
                    time.sleep(0.02)
            yield
        finally:
            os.close(fd)

    def token(self, create=False):
        if create and not self.record_path.exists():
            fd = private_file(self.record_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as stream:
                json.dump({"token": secrets.token_hex(32)}, stream)
        with os.fdopen(private_file(self.record_path, os.O_RDONLY)) as stream:
            try:
                token = json.load(stream)["token"]
                if not isinstance(token, str) or len(token) != 64:
                    raise ValueError("Malformed token")
                bytes.fromhex(token)
                return token
            except (ValueError, KeyError, TypeError) as error:
                raise RecoveryError("Invalid ownership record; refusing service control") from error

    def verify(self, properties):
        identity = self.identity
        token = self.token()
        commands = properties.get("ExecStart", [])
        valid = (
            properties.get("Transient")
            and properties.get("Description") == identity.description
            and len(commands) == 1
            and list(commands[0][:3]) == [identity.argv[0], identity.argv, False]
            and f"LINUX_CUSTOM_DIMMER_OWNER={token}" in properties.get("Environment", [])
            and properties.get("KillMode") == "control-group"
            and properties.get("Restart") == "no"
            and properties.get("TimeoutStopUSec") == 2_000_000
            and properties.get("SendSIGKILL")
        )
        if not valid:
            raise RecoveryError("Service identity mismatch; refusing to start, stop, or kill it")

    def perform(self, action, *, runtime_limit=None):
        if action not in {"launch", "stop", "kill"}:
            raise RecoveryError("Unknown action")
        with self.locked(), self.backend.pinned(self.identity.unit) as existing:
            if existing is not None:
                self.verify(existing)
                if action == "launch":
                    state = existing.get("ActiveState", "unknown")
                    if state in {"active", "activating"}:
                        return "Already running"
                    raise RecoveryError(f"Service is {state}; wait for cleanup and retry launch")
                self.backend.stop(self.identity.unit, action == "kill")
                return "Stopped"
            if action != "launch":
                return "Already stopped"
            token = self.token(create=True)
            environment = {
                key: os.environ[key]
                for key in (
                    "WAYLAND_DISPLAY",
                    "XDG_RUNTIME_DIR",
                    "DBUS_SESSION_BUS_ADDRESS",
                    "XDG_SESSION_TYPE",
                    "XDG_CURRENT_DESKTOP",
                    "LANG",
                    "LC_ALL",
                )
                if key in os.environ
            }
            environment["QT_QPA_PLATFORM"] = "wayland"
            self.backend.start(self.identity, token, environment, runtime_limit)
            return "Launched"


def parse_action(argv=None):
    parser = argparse.ArgumentParser(
        description="Launch or recover Linux Custom Dimmer", allow_abbrev=False
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--stop", action="store_true", help="Stop the verified dimmer service")
    group.add_argument("--kill", action="store_true", help="Immediately kill the verified service")
    args = parser.parse_args(argv)
    return "kill" if args.kill else "stop" if args.stop else "launch"


def main(argv=None):
    action = parse_action(argv)
    from .service import Systemd

    try:
        root = Path(__file__).resolve().parents[2]
        runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
        print(Controller(Identity(root), runtime, Systemd()).perform(action))
        return 0
    except (RecoveryError, OSError) as error:
        print(f"dimmer: {error}", file=__import__("sys").stderr)
        return 1
