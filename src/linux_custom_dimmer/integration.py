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
            keys = self.manager.shortcut(ACTION, timeout=2)
            path = self.manager.getComponent(COMPONENT, timeout=2)
            component = dbus.Interface(
                self.bus.get_object("org.kde.kglobalaccel", path), "org.kde.kglobalaccel.Component"
            )
            return list(keys) == [KEY] and bool(component.isActive(timeout=2))
        except dbus.DBusException:
            return False

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

    def install(self):
        self.check_files()
        if not self.shortcuts.available():
            raise RuntimeError(
                "Ctrl+Alt+Shift+D is already assigned; existing shortcut was preserved"
            )
        if all(path.exists() for path in self.entries()) and self.shortcuts.registered():
            return
        with ExitStack() as rollback:
            rollback.callback(self.refresh)
            for path, text in self.entries().items():
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("x") as stream:
                        rollback.callback(path.unlink, missing_ok=True)
                        stream.write(text)
            self.refresh()
            rollback.callback(self.shortcuts.unregister)
            self.shortcuts.register()
            self.verify()
            rollback.pop_all()

    def uninstall(self):
        self.check_files()
        self.shortcuts.unregister()
        for path in self.entries():
            path.unlink(missing_ok=True)
        self.refresh()
