# Linux custom dimmer

A small neutral overlay for this Ubuntu KDE Wayland laptop. Stage 1 prepares
the native bridge and independent recovery. Product controls are Stage 2 work.
No overlay is created by the current launcher.

## Development setup

Use Ubuntu's Qt/PyQt6 and LayerShellQt together. Never install PyQt6 or
PyQt6-Qt6 from pip into this project.

```sh
./scripts/setup-dev
./scripts/check
```

No sudo is needed on this laptop. The setup script uses its existing Python,
pip, compiler, `dpkg`/APT, `wayland-info`, and Qt/PyQt6/dbus runtimes. It creates
`.venv` with system packages visible, installs pinned developer tools including
CMake/Ninja there, and installs this Python package editable without runtime
dependencies. `venv --without-pip` uses Ubuntu's existing pip without the separate
ensurepip package. Pip still writes only inside the venv.

`scripts/prepare-headers` reads the installed Qt/LayerShellQt package versions,
downloads exactly matching Ubuntu development packages into `.local/debs`,
and extracts them under `.local/sysroot`. This is archive extraction, not a
system package installation; no maintainer scripts run. The native bridge links
directly to the existing `/usr/lib` runtime libraries. It does not copy or load
a second Qt runtime. Headers need to remain available at the configured Ubuntu
APT repository version. If that version is unavailable, setup stops with the
APT error instead of selecting mismatched headers.

The result is `build/native/libdimmer_layer_shell.so`. Run setup again after
system Qt updates. It does not install desktop integration. The adapter requires
matching Qt compile/runtime versions and LayerShellQt 6.6 or newer. Generated
binaries, downloaded packages, caches, and environments are ignored by Git.

`scripts/check` builds, checks imports and Python compilation, runs Ruff, and
executes offscreen/unit tests. It does not connect to the desktop or signal
services. Real recovery tests are explicit:

```sh
DIMMER_LIVE_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_recovery.py
DIMMER_KDE_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_kde_route.py
./scripts/probe-native
```

Recovery tests create only disposable services with external runtime deadlines
and a disposable sentinel. The KDE test creates and removes one temporary
desktop entry, binds no key, and invokes KDE's actual external command route.
The native probe never maps a visible window or paints pixels. Its Qt timer
exits after 250 ms and systemd terminates it within six seconds even if frozen.
Protocol diagnostics remain in ignored `.local/native-probe.log`.

## Launch and recovery contract

```sh
./bin/dimmer         # Stage 1 stub exits without a window; Stage 2 opens Stopped
./bin/dimmer --stop  # independent graceful service shutdown, two-second timeout
./bin/dimmer --kill  # independent immediate termination of the verified service
```

The CLI uses system Python and distro `dbus-python`; it needs neither Qt nor a
working venv for recovery. Only launch uses `.venv/bin/python3`.
It accepts no PID, unit, command, or opacity arguments. A fixed transient user
service prevents multiple instances. Stage 2 will add showing the existing UI.

Before service control, the launcher checks its exact executable/argument list,
project identity, safety properties, and random token in an owner-only runtime
record. It holds a systemd unit reference while checking and stopping, preventing
unit collection and name reuse between those steps. A mismatch is an error.
This protects against accidental collisions; it is not a security boundary
against malicious code already running as the same user.

Runtime files are in `$XDG_RUNTIME_DIR/linux-custom-dimmer/`, mode 0700, with
mode-0600 `owner.json` and `control.lock`. Do not delete them while the app runs.
There is no PID file or background recovery daemon. systemd supplies
`Restart=no`, `KillMode=control-group`, `TimeoutStopSec=2s`, and
`SendSIGKILL=yes`; the service is bound to the active graphical session.

If the launcher files themselves are unavailable, the direct manager command is:

```sh
systemctl --user stop linux-custom-dimmer.service
```

That manual command bypasses the launcher's identity checks. Use it only for the
known dimmer service. Normal recovery uses `bin/dimmer`.

## Native boundary and Stage 2 contract

Call `support.check_session()` and verify independent recovery before creating
any visible overlay. The support check runs the installed `wayland-info` once,
with a two-second deadline, and requires KDE Wayland and the layer-shell protocol.
It rejects a global shell override.

`NativeBridge.configure(window)` accepts a live caller-owned `QWindow` on the
GUI thread before its native surface exists. It preserves the Python object and
GIL through the C call, checks Qt versions and bridge ABI, and retains no pointer.
The C adapter uses public LayerShellQt calls on that window only. It sets the
overlay layer, four anchors, exclusive zone -1, no keyboard interactivity, and
Qt input-transparent/no-focus flags. It does not draw, globally select a shell,
change hardware brightness, or create a control window. The caller destroys the
window if configuration or later surface creation fails.

The pure `State` class starts Stopped at 50%, validates integers 0..80, keeps
stopped adjustments inactive, and stops at zero. It is a transition contract;
the Stage 2 controller must validate support/recovery and successful rendering
before committing an Active transition.

## Desktop integration and removal

No permanent launcher, shortcut, service file, autostart entry, or plugin is
installed in Stage 1. See [KDE integration](docs/kde-integration.md) for the
verified command route and the Stage 2 binding procedure.

To remove this development checkout, stop it with `./bin/dimmer --stop`, then
remove the project directory. After the service has stopped, its private runtime
directory can also be removed; logout removes it automatically. All build tools
and extracted headers added during Stage 1 are inside this project. Existing
Ubuntu runtime packages remain untouched.

Read [status](docs/status.md), [verification](docs/verification.md),
[testing](docs/testing.md), and [issues and decisions](docs/issues-and-decisions.md)
before the next stage. The next instruction is `build the app` only after Stage 1
build and recovery prerequisites pass.
