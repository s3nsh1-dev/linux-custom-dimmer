"""Event-driven lock/suspend/display guards; never resume dimming automatically."""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtDBus import (
    QDBusConnection,
    QDBusInterface,
    QDBusMessage,
    QDBusServiceWatcher,
    QDBusVariant,
)


def builtin_screen(screens):
    candidates = [
        screen for screen in screens if screen.name().startswith(("eDP-", "LVDS-", "DSI-"))
    ]
    if len(candidates) != 1:
        raise RuntimeError("Connect one built-in laptop display to use extra dimming")
    return candidates[0]


class SessionGuard(QObject):
    unsafe = pyqtSignal(str)

    def __init__(self, app):
        super().__init__()
        self.connected = False
        self.locked = False
        self.sleeping = False
        self.app = app
        self.watched = set()
        app.screenAdded.connect(self.screen_added)
        app.screenRemoved.connect(self.topology_changed)
        for screen in app.screens():
            self.watch_screen(screen)

    def watch_screen(self, screen):
        if screen in self.watched:
            return
        self.watched.add(screen)
        for signal in (
            screen.geometryChanged,
            screen.virtualGeometryChanged,
            screen.logicalDotsPerInchChanged,
            screen.refreshRateChanged,
        ):
            signal.connect(self.topology_changed)
        screen.destroyed.connect(lambda: self.watched.discard(screen))

    def screen_added(self, screen):
        self.watch_screen(screen)
        self.topology_changed()

    def topology_changed(self, *args):
        self.unsafe.emit("Display changed. Press Start to resume.")

    @pyqtSlot(bool)
    def lock_changed(self, locked):
        self.locked = locked
        self.unsafe.emit(
            "Session locked." if locked else "Session unlocked. Press Start to resume."
        )

    @pyqtSlot()
    def about_to_lock(self):
        self.lock_changed(True)

    @pyqtSlot(bool)
    def sleep_changed(self, sleeping):
        self.sleeping = sleeping
        self.unsafe.emit("Preparing to sleep." if sleeping else "Resumed. Press Start to resume.")

    def connection_lost(self, *args):
        self.connected = False
        self.unsafe.emit("Session or recovery service changed. Restart the dimmer.")

    def connect_dbus(self):
        session = QDBusConnection.sessionBus()
        system = QDBusConnection.systemBus()
        if not session.isConnected() or not system.isConnected():
            raise RuntimeError("Session safety monitoring is unavailable")
        subscriptions = [
            session.connect(
                "org.freedesktop.ScreenSaver",
                "/ScreenSaver",
                "org.freedesktop.ScreenSaver",
                "ActiveChanged",
                self.lock_changed,
            ),
            session.connect(
                "org.freedesktop.ScreenSaver",
                "/ScreenSaver",
                "org.kde.screensaver",
                "AboutToLock",
                self.about_to_lock,
            ),
            system.connect(
                "org.freedesktop.login1",
                "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager",
                "PrepareForSleep",
                self.sleep_changed,
            ),
        ]
        if not all(subscriptions):
            raise RuntimeError("Could not subscribe to session safety events")
        self.screensaver = QDBusInterface(
            "org.freedesktop.ScreenSaver", "/ScreenSaver", "org.freedesktop.ScreenSaver", session
        )
        self.login = QDBusInterface(
            "org.freedesktop.login1",
            "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager",
            system,
        )
        self.screensaver.setTimeout(1000)
        self.login.setTimeout(1000)
        if not self.screensaver.isValid() or not self.login.isValid():
            raise RuntimeError("Lock or suspend service unavailable")
        self.watchers = []
        for name, bus in [
            ("org.freedesktop.ScreenSaver", session),
            ("org.kde.kglobalaccel", session),
            ("org.freedesktop.login1", system),
        ]:
            watcher = QDBusServiceWatcher(
                name, bus, QDBusServiceWatcher.WatchModeFlag.WatchForOwnerChange, self
            )
            watcher.serviceOwnerChanged.connect(self.connection_lost)
            self.watchers.append(watcher)
        self.connected = True
        self.ensure_unlocked()

    def ensure_unlocked(self):
        if not self.connected:
            raise RuntimeError("Session safety monitoring is unavailable. Restart the app.")
        reply = self.screensaver.call("GetActive")
        if reply.type() == QDBusMessage.MessageType.ErrorMessage or len(reply.arguments()) != 1:
            raise RuntimeError("Could not confirm session unlock state")
        properties = QDBusInterface(
            "org.freedesktop.login1",
            "/org/freedesktop/login1",
            "org.freedesktop.DBus.Properties",
            QDBusConnection.systemBus(),
        )
        properties.setTimeout(1000)
        reply_sleep = properties.call("Get", "org.freedesktop.login1.Manager", "PreparingForSleep")
        if (
            reply_sleep.type() == QDBusMessage.MessageType.ErrorMessage
            or len(reply_sleep.arguments()) != 1
        ):
            raise RuntimeError("Could not confirm suspend state")
        sleeping = reply_sleep.arguments()[0]
        if isinstance(sleeping, QDBusVariant):
            sleeping = sleeping.variant()
        if type(sleeping) is not bool:
            raise RuntimeError("Invalid suspend state response")
        if reply.arguments()[0] or self.locked or self.sleeping or sleeping:
            raise RuntimeError("Unlock or resume the session before starting dimming")
