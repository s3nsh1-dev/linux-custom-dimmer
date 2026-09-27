"""Typed systemd D-Bus boundary; service references prevent unit-name reuse."""

import time
from contextlib import contextmanager

import dbus

from .control import RecoveryError

DEST = "org.freedesktop.systemd1"
BASE = "/org/freedesktop/systemd1"
UNIT = DEST + ".Unit"
SERVICE = DEST + ".Service"
PROPERTIES = "org.freedesktop.DBus.Properties"


class Systemd:
    def __init__(self):
        try:
            self.bus = dbus.SessionBus(private=True)
            self.manager = dbus.Interface(self.bus.get_object(DEST, BASE), DEST + ".Manager")
        except dbus.DBusException as error:
            raise RecoveryError(f"User service manager unavailable: {error}") from error
        self.objects = {}

    @contextmanager
    def pinned(self, name):
        obj = None
        try:
            try:
                # Ref before reading identity. A pinned unit cannot be collected and replaced.
                self.manager.RefUnit(name, timeout=2)
            except dbus.DBusException as error:
                if error.get_dbus_name() != DEST + ".NoSuchUnit":
                    raise
                yield None
                return
            try:
                path = self.manager.GetUnit(name, timeout=2)
                obj = self.bus.get_object(DEST, path)
                self.objects[name] = obj
                properties = dbus.Interface(obj, PROPERTIES)
                values = dict(properties.GetAll(UNIT, timeout=2))
                values.update(properties.GetAll(SERVICE, timeout=2))
                yield values
            finally:
                self.objects.pop(name, None)
                self.manager.UnrefUnit(name, timeout=2)
        except dbus.DBusException as error:
            raise RecoveryError(f"User service operation failed: {error}") from error

    def start(self, identity, token, environment, runtime_limit=None):
        try:
            target = self.bus.get_object(
                DEST, self.manager.GetUnit("graphical-session.target", timeout=2)
            )
            if dbus.Interface(target, PROPERTIES).Get(UNIT, "ActiveState") != "active":
                raise RecoveryError("No active graphical session; refusing launch")
            properties = {
                "Description": identity.description,
                "Type": "exec",
                "Restart": "no",
                "KillMode": "control-group",
                "TimeoutStopUSec": dbus.UInt64(2_000_000),
                "SendSIGKILL": True,
                "CollectMode": "inactive-or-failed",
                "BindsTo": dbus.Array(["graphical-session.target"], signature="s"),
                "After": dbus.Array(["graphical-session.target"], signature="s"),
                "ExecStart": dbus.Array(
                    [(identity.argv[0], dbus.Array(identity.argv, signature="s"), False)],
                    signature="(sasb)",
                ),
                "Environment": dbus.Array(
                    [f"{key}={value}" for key, value in environment.items()]
                    + [f"LINUX_CUSTOM_DIMMER_OWNER={token}"],
                    signature="s",
                ),
                "UnsetEnvironment": dbus.Array(
                    [
                        "QT_WAYLAND_SHELL_INTEGRATION",
                        "QT_PLUGIN_PATH",
                        "QT_QPA_PLATFORM_PLUGIN_PATH",
                        "PYTHONPATH",
                        "PYTHONHOME",
                        "LD_PRELOAD",
                        "LD_LIBRARY_PATH",
                    ],
                    signature="s",
                ),
            }
            if runtime_limit is not None:
                properties["RuntimeMaxUSec"] = dbus.UInt64(runtime_limit * 1_000_000)
            self.manager.StartTransientUnit(
                identity.unit,
                "fail",
                list(properties.items()),
                dbus.Array([], signature="(sa(sv))"),
                timeout=2,
            )
        except dbus.DBusException as error:
            raise RecoveryError(f"Could not launch dedicated service: {error}") from error

    def stop(self, name, immediate):
        obj = self.objects[name]
        unit = dbus.Interface(obj, UNIT)
        if immediate:
            unit.Kill("all", 9, timeout=2)
        unit.Stop("replace", timeout=2)
        deadline = time.monotonic() + 3
        properties = dbus.Interface(obj, PROPERTIES)
        while properties.Get(UNIT, "ActiveState", timeout=2) not in {"inactive", "failed"}:
            if time.monotonic() >= deadline:
                raise RecoveryError("Service did not stop within three seconds")
            time.sleep(0.02)
