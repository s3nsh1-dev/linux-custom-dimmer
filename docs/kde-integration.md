# KDE external recovery route

Stage 1 verified this on Plasma 6.6.6. It is a command launched by KDE's existing
global shortcut service, outside the dimmer process and service group.

The real probe created
`~/.local/share/kglobalaccel/linux-custom-dimmer-stage1-probe.desktop`, containing
an `Exec` command for a fixed test recovery script, `StartupNotify=false`,
`X-KDE-GlobalAccel-CommandShortcut=true`, and `X-KDE-Shortcuts=none`.
It refused an existing file, registered its `_launch` action through
`org.kde.KGlobalAccel.doRegister`, then used the component's `invokeShortcut`
D-Bus method. KDE launched an independent process that killed the verified,
deliberately frozen dummy. The unrelated sentinel survived. The measured
dispatch-to-exit interval was 0.213 seconds.

The test removed its file and called `unregister(component, "_launch")`, then
refreshed the desktop cache with `kbuildsycoca6 --noincremental`. A subsequent
`getComponent` returned `NoSuchComponent`. No permanent key assignment remains.

`Ctrl+Alt+Shift+D` has Qt combined key value `234881092`. The read-only call
below returned `true`, meaning free at the time of the test:

```sh
qdbus6 org.kde.kglobalaccel /kglobalaccel \
  org.kde.KGlobalAccel.isGlobalShortcutAvailable \
  234881092 linux-custom-dimmer-emergency.desktop
```

For Stage 2, check availability again and create only owned entries. The planned
emergency command is the absolute project path to `bin/dimmer --kill`, quoted
using desktop-entry escaping, not shell interpolation. Use an emergency menu
entry under `$XDG_DATA_HOME/applications/` and the external command registration
under `$XDG_DATA_HOME/kglobalaccel/`. Default XDG data home is `~/.local/share`.
Register the command's `_launch` action with the available key using the typed
KGlobalAccel D-Bus API. Do not overwrite an existing assignment or rewrite the
entire shortcut configuration. The daemon may record owned entries in
`~/.config/kglobalshortcutsrc` and its own state file; remove only this component
through the API on uninstall.

The Stage 1 probe proves KDE command dispatch while the target is frozen.
It does not prove physical key delivery, menu interaction, or behavior under
an active dimming overlay. Those are required Stage 2 live checks, including
focus in another app and a frozen dimmer with an independent fallback deadline.

KDE's implementation loads command desktop entries from `kglobalaccel/` and
launches the `_launch` action via `KIO::ApplicationLauncherJob`. See the
[registry implementation](https://raw.githubusercontent.com/KDE/kglobalacceld/master/src/globalshortcutsregistry.cpp)
and [command component](https://raw.githubusercontent.com/KDE/kglobalacceld/master/src/kserviceactioncomponent.cpp).
The checked local D-Bus interfaces and live probe determine compatibility here.
