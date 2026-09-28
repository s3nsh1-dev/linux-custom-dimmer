"""Reversible current-user desktop entries and KDE's independent recovery key."""

import os
import subprocess
from contextlib import ExitStack
from pathlib import Path

import dbus

from .control import Identity

COMPONENT = "linux-custom-dimmer-emergency.desktop"
KEY = 234881092  # Ctrl+Alt+Shift+D, Qt's combined key code.
ACTION = [COMPONENT, "_launch", "Linux Custom Dimmer emergency", "Emergency stop and quit"]


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


class KDEShortcuts:
    def __init__(self):
        self.bus = dbus.SessionBus()
        self.manager = dbus.Interface(
            self.bus.get_object("org.kde.kglobalaccel", "/kglobalaccel"), "org.kde.KGlobalAccel"
        )

    def available(self):
        return bool(self.manager.isGlobalShortcutAvailable(KEY, COMPONENT, timeout=2))

    def registered(self):
        try:
            return self.snapshot() == ([KEY], True)
        except dbus.DBusException:
            return False

    def snapshot(self):
        try:
            path = self.manager.getComponent(COMPONENT, timeout=2)
        except dbus.DBusException as error:
            if error.get_dbus_name() == "org.kde.kglobalaccel.NoSuchComponent":
                return None
            raise
        component = dbus.Interface(
            self.bus.get_object("org.kde.kglobalaccel", path), "org.kde.kglobalaccel.Component"
        )
        names = list(component.shortcutNames(timeout=2))
        if not names:
            # KDE may retain an empty component after unregistering its last action.
            return None
        if names != ["_launch"]:
            raise RuntimeError("Cannot confirm ownership of unexpected emergency actions")
        return list(self.manager.shortcut(ACTION, timeout=2)), bool(component.isActive(timeout=2))

    def restore(self, snapshot):
        if snapshot is None:
            self.unregister()
            return
        keys, active = snapshot
        self.manager.doRegister(ACTION, timeout=2)
        self.manager.setShortcut(
            ACTION, dbus.Array(keys, signature="i"), dbus.UInt32(6 if active else 4), timeout=2
        )
        if not active:
            self.manager.setInactive(ACTION, timeout=2)
        if self.snapshot() != snapshot:
            raise RuntimeError("Could not restore the previous owned shortcut registration")

    def register(self):
        self.manager.doRegister(ACTION, timeout=2)
        keys = self.manager.setShortcut(
            # NoAutoloading | SetPresent: saving the key alone does not activate it.
            ACTION,
            dbus.Array([KEY], signature="i"),
            dbus.UInt32(6),
            timeout=2,
        )
        if list(keys) != [KEY] or not self.registered():
            raise RuntimeError("KDE did not activate the emergency shortcut")

    def unregister(self):
        self.manager.unregister(COMPONENT, "_launch", timeout=2)


def refresh_cache():
    subprocess.run(
        ["/usr/bin/kbuildsycoca6", "--noincremental"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=10,
    )


class Integration:
    def __init__(self, root, data_home=None, shortcuts=None, refresh=refresh_cache):
        self.root = root
        self.data_home = data_home or Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
        )
        self.shortcuts = shortcuts if shortcuts is not None else KDEShortcuts()
        self.refresh = refresh

    def entries(self):
        common = (
            "[Desktop Entry]\nType=Application\nTerminal=false\nStartupNotify=false\n"
            "Categories=Utility;\nIcon=display-brightness-symbolic\n"
            f"X-Linux-Custom-Dimmer-Owner={Identity(self.root).description}\n"
        )
        command = desktop_quote(self.root / "bin/dimmer")
        return {
            self.data_home / "applications/linux-custom-dimmer.desktop": common
            + f"Name=Linux Custom Dimmer\nComment=Neutral extra screen dimming\nExec={command}\n",
            self.data_home / f"applications/{COMPONENT}": common
            + "Name=Dimmer emergency stop\nComment=Stop the dimmer even if it is frozen\n"
            + f"Exec={command} --kill\nX-KDE-Shortcuts=Ctrl+Alt+Shift+D\n",
        }

    def check_files(self, required=False):
        for path, text in self.entries().items():
            if path.is_symlink() or (path.exists() and path.read_text() != text):
                raise RuntimeError(f"Refusing unrelated or modified desktop entry: {path}")
            if required and not path.is_file():
                raise RuntimeError(
                    "Install the emergency shortcut first: run scripts/install-local"
                )

    def verify(self):
        self.check_files(required=True)
        if not self.shortcuts.registered():
            raise RuntimeError("Emergency shortcut unavailable. Run scripts/install-local.")

    def owned_registration(self):
        snapshot = self.shortcuts.snapshot()
        emergency = self.data_home / f"applications/{COMPONENT}"
        if snapshot is not None and not emergency.is_file():
            raise RuntimeError("Cannot confirm ownership of the existing emergency shortcut")
        return snapshot

    def install(self):
        self.check_files()
        previous = self.owned_registration()
        if all(path.exists() for path in self.entries()) and self.shortcuts.registered():
            return
        # KDE's availability query includes our own action in the current context.
        # Retaining an already owned key needs no new key reservation.
        if (previous is None or previous[0] != [KEY]) and not self.shortcuts.available():
            raise RuntimeError(
                "Ctrl+Alt+Shift+D is already assigned; existing shortcut was preserved"
            )
        with ExitStack() as rollback:
            rollback.callback(self.refresh)
            rollback.callback(self.shortcuts.restore, previous)
            for path, text in self.entries().items():
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("x") as stream:
                        rollback.callback(path.unlink, missing_ok=True)
                        stream.write(text)
            self.refresh()
            self.shortcuts.register()
            self.verify()
            rollback.pop_all()

    def uninstall(self):
        self.check_files()
        if self.owned_registration() is not None:
            self.shortcuts.unregister()
        for path in self.entries():
            path.unlink(missing_ok=True)
        self.refresh()
