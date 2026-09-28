# Linux Custom Dimmer

A small native app for neutral extra dimming on this Ubuntu KDE Wayland laptop.
It places a transparent black layer over the built-in display. Hardware
brightness, Night Light and power settings stay under your control.

The app is built and installed locally. Automated and real-process recovery
checks have passed; hands-on input, physical shortcut, and session-transition
acceptance remain pending at the owner's request. See [verification](docs/verification.md).
The version remains `0.1.0.dev0` until those checks pass.

## Use

Launch **Linux Custom Dimmer** from the application menu, or run:

```sh
./bin/dimmer
```

It opens **Stopped** at 50%. Select **Extra dimming**, then **Start**.
The slider accepts 0–80%; higher is darker. Adjusting it while stopped only
selects the next level. **Stop** removes the layer and keeps the window open;
0% also stops. Closing the window or **Emergency stop and quit** exits and
removes the layer. Minimize may retain dimming. Launching again shows the same
instance. Lock, suspend, or a display change stops dimming; resume explicitly.

To recover independently of the app, including if its UI freezes:

- Press **Ctrl+Alt+Shift+D**.
- Launch **Dimmer emergency stop** from the application menu.
- Run `./bin/dimmer --kill` for immediate recovery, or `./bin/dimmer --stop`
  for graceful shutdown with a two-second forced-stop fallback.

If the checkout is unavailable, the direct fallback is:

```sh
systemctl --user stop linux-custom-dimmer.service
```

That direct command bypasses the launcher's identity checks; use it for the
known dimmer unit. The menu command and shortcut were exercised against the
frozen real app; physical key delivery still needs the hands-on check.

The 80% cap is not a visibility guarantee. Choose darkness by eye. Opacity is
not calibrated physical brightness. Black adds no tint of its own and does not
cancel an independently enabled Night Light tint.

## Setup and checks

Development, installation, use, and removal need no sudo on this laptop.

```sh
./scripts/setup-dev
./scripts/check
./scripts/install-local
```

Tested environment: Ubuntu 26.04.1, Plasma 6.6.6, Wayland, Python 3.14.4,
PyQt6/Qt 6.10.2 and LayerShellQt 6.6.4. Support is limited to one built-in
laptop display, discovered from the connector reported by Qt. External-monitor
controls, GNOME, X11, tray integration and public packaging are outside scope.
Start is disabled if required support or independent recovery cannot be verified.

Setup uses the existing distro Python, pip, compiler, `dpkg`/APT, Qt/PyQt6,
dbus-python and `wayland-info`. It creates a project `.venv` with system packages
visible, installs pinned development tools, and installs this package editable.
Matching Qt/LayerShellQt headers are downloaded and extracted under `.local/`;
no system package installation or maintainer script is run. The native adapter
links to the existing system runtime libraries. Do not install another PyQt6/Qt
runtime with pip. Run setup again after a system Qt update. If matching header
packages are unavailable, setup stops instead of choosing different versions.

`scripts/check` builds the adapter, checks imports, compilation, lint/formatting,
and runs offscreen and unit tests. Some sandboxed agents need ordinary-user tool
access to bind the temporary Unix sockets used by tests. No desktop or live
service operation is part of the default checks.

Explicit live tests create their own bounded services and clean up afterward:

```sh
DIMMER_LIVE_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_recovery.py
DIMMER_KDE_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_kde_route.py
DIMMER_APP_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_app.py
.venv/bin/python3 tests/integration/app_probe.py
```

The last two commands briefly dim the actual display; close any existing dimmer
first. Each app test has its own quit timer and an independent systemd runtime
limit. The native-only `./scripts/probe-native` configures unmapped windows.
See [testing](docs/testing.md) for hands-on acceptance and resource methodology.

For repeatable resource samples, close the dimmer first:

```sh
./scripts/measure-resources --workload idle
./scripts/measure-resources --workload video
```

Each command runs OFF/ON/OFF at 65%, default three minutes per phase, with a
hard app expiry. The sampler minimizes the controls; leave the app and system
brightness unchanged until it closes both test windows. `--seconds 60` selects a shorter comparison. Video uses the
existing ffmpeg/ffplay and a generated local test clip. Raw readings remain in
ignored `.local/`. These readings do not establish battery-life savings.

## Local integration and removal

`install-local` creates exactly two application entries under
`${XDG_DATA_HOME:-~/.local/share}/applications/`:

- `linux-custom-dimmer.desktop`
- `linux-custom-dimmer-emergency.desktop`

The emergency entry supplies KDE's external command shortcut. KDE stores its
owned component in the user's shortcut configuration through its D-Bus API.
The installer preserves conflicting files and key assignments and can be rerun.
The entries refer to this checkout's absolute path; uninstall before moving it.
No root service, autostart entry, permanent service file, plugin, or extra
background daemon is installed.

```sh
./scripts/uninstall-local
```

This stops the verified app first and removes its entries and shortcut. It
refuses modified or unrelated entries. You may then remove the project directory,
which contains every build tool and header added for development. The private
`$XDG_RUNTIME_DIR/linux-custom-dimmer/` directory can be removed after the app
has stopped; logout clears it automatically. Existing system packages stay intact.

## Implementation and troubleshooting

The control window is Qt Widgets. A raster `QWindow` and `QBackingStore` paint
black with source alpha only on exposure, resize, or a changed opacity. There is
no screen capture or idle repaint timer. A narrow project-built C++ adapter uses
public LayerShellQt APIs on that window alone, checks Qt compatibility and GUI
thread use, and configures input transparency with no keyboard focus.

One transient `linux-custom-dimmer.service` holds the Python application. The
Qt-free recovery launcher uses system Python and dbus-python and works even if
the venv or GUI is broken. Before controlling the service it verifies the exact
executable, arguments, project identity, private token and shutdown properties,
while holding a systemd reference to prevent name reuse. This prevents accidental
collisions; it is not a boundary against malicious code running as the same user.
A private bounded Unix socket accepts only fixed application actions.

If Start is disabled, read the message in the window. Repair local integration
with `./scripts/install-local`, rebuild after Qt updates with `./scripts/setup-dev`,
and relaunch. Inspect app errors with:

```sh
journalctl --user -u linux-custom-dimmer.service -b --no-pager
```

[Status](docs/status.md), [verification](docs/verification.md),
[KDE integration](docs/kde-integration.md), and
[issues and decisions](docs/issues-and-decisions.md) record results, limitations,
and commits. The owner's repository is
[s3nsh1-dev/linux-custom-dimmer](https://github.com/s3nsh1-dev/linux-custom-dimmer).
The code remains a development version with the acceptance checks above pending;
no release tag has been created.
