# Project status

Updated: 2026-09-27.

## Current stage

Stage 2 is in progress on `stage-2-app`. Native controls and the raster overlay
pass 120 default tests and seven real-app lifecycle/recovery tests. Session
guards and local integration are implemented; hands-on acceptance and resource
measurements are in progress.
The owner requires ordinary-account development and runtime with minimal
privileges. No sudo or system package installation was used.

## Local history

Current branch: `stage-2-app`, from Stage 1 handoff `ff28a31`.

- `a5a8a67` — initial agreed scope and evidence.
- `35dadec` — rootless development environment, matching headers, native adapter.
- `68c22cf` — independent launch/recovery, unit identity checks, live process tests.
- `a8ccdec` — state contract, bounded unmapped probe, and Stage 1 handoff.
- `0812c8e` — final review fixes and failure-path regression tests.
- `ff28a31` — Stage 1 completion record.
- `ba108e0` — native overlay and controls, rendering and UI tests.
- Lifecycle, local IPC, menu/shortcut integration checkpoint follows `ba108e0`.

No remote, push, publication, or release tag exists. Open-source distribution
remains the owner's later decision. Build output and downloaded tools are ignored.

## Reproduce the setup and checks

```sh
./scripts/setup-dev
./scripts/check
DIMMER_LIVE_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_recovery.py
DIMMER_KDE_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_kde_route.py
./scripts/probe-native
```

Setup works without admin rights on this laptop, using the existing system
Python/pip/compiler. It creates `.venv` with access to distro packages, installs
pinned tools there, downloads exact-version distro headers into `.local/debs`,
extracts them into `.local/sysroot`, and builds `build/native/`.
It installs this package editable with no pip runtime dependencies.
Re-run setup after system Qt updates. Do not pip-install another Qt runtime.

Observed environment: Ubuntu 26.04.1, Plasma 6.6.6, Wayland, Python 3.14.4,
PyQt6/Qt 6.10.2, LayerShellQt 6.6.4, dbus-python 1.4.0, GCC 15.2.0,
systemd 259.5. Added tools: CMake 4.2.3, Ninja 1.13.0, pytest 9.0.2, Ruff 0.15.7,
setuptools 82.0.1, iniconfig 2.3.0, pluggy 1.6.0, inside `.venv` only.
The downloaded development packages match the installed Ubuntu runtime versions.
No system packages were installed or changed; no plugin is needed.

## Stage 1 results (historical)

- Rootless setup and repeat setup passed. Strict native compile, Qt imports,
  Python compilation, Ruff, formatting, and 72 default tests passed. Plain pytest also passed 72, with 5 live cases skipped.
- Four live service tests passed. Frozen dummy plus child stopped in 2.315s;
  independent kill took 0.272s. Unrelated sentinel survived. Concurrency,
  wrong-identity refusal, and automatic external deadline were verified.
- KDE command test passed in 0.127s after the review fixes. Ctrl+Alt+Shift+D was available, but no key
  was bound. Temporary desktop file and registration were removed.
- Native probe succeeded in 516ms with only unmapped windows. It had a Qt timer
  and an independent systemd deadline. No pixels or dimming were displayed.
- The main Stage 1 service entry point prints an explanatory line and exits.
  `bin/dimmer --stop` and `--kill` are independent of Qt and the venv.

Stage 1 left private ownership and lock files under
`$XDG_RUNTIME_DIR/linux-custom-dimmer/`. Test runs create
similarly private directories named for their disposable units; this session
removed those after confirming their services were absent. Logout removes
runtime files. They are not processes or startup registrations.
At that handoff no permanent application menu entry or shortcut existed.
The KDE test temporarily used
`~/.local/share/kglobalaccel/linux-custom-dimmer-stage1-probe.desktop` and removed
it. Final inventory confirms zero dimmer/test units and zero dimmer timers;
no dimmer, sentinel, or probe remains running.

## Stage 2 implementation and current evidence

- Native controls: Stopped at 50%, range 0–80%, explicit Start/Stop, zero-stop,
  immediate emergency quit and close cleanup. Raster layer paints on demand.
- Lock/suspend/output notifications stop the layer and never restart it.
  Start verifies session state, native bridge, service identity, installed
  emergency command, and the active shortcut assignment.
- Private bounded Unix socket handles fixed validated actions; relaunch shows
  the existing window. Qt-free recovery remains independent of this socket.
- Installed user menu entries `linux-custom-dimmer.desktop` and
  `linux-custom-dimmer-emergency.desktop`, plus Ctrl+Alt+Shift+D through KDE.
  No system packages, system services, autostart, or extra daemon were added.
- `scripts/check`: 120 passed, 12 live tests deselected. The tool sandbox needs
  its ordinary-user escape to allow local Unix sockets; this is not sudo.
- `DIMMER_APP_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_app.py`:
  seven passed. Each app expires after 15 seconds and has an inner quit timer.
  Frozen app recovery: KDE command 0.256s, menu command 0.588s, graceful stop
  0.315s. Sentinel survived. Quit, SIGTERM, SIGKILL, duplicate launches and
  zero/Stop cleanup passed. These prove command dispatch, not physical key input.
- Earlier 20-second probe: 50/65/80% each active, one paint per change, no idle
  repaint; 0% removed the layer. Every test ended with its service absent.

Raw native diagnostics and setup output remain under ignored `.local/`.
See `docs/verification.md` for actual results and limitations, and
`docs/kde-integration.md` for the external shortcut mechanism.

## Remaining work and next action

Continue authorized Stage 2 Tasks 4–6. Finish live acceptance for the
implemented controls, lifecycle guards and emergency route.
Verify visible neutrality, input passing, frozen-app key recovery, desktop
lifecycle behavior, and final idle/video resource use. No product release or
`v0.1.0` tag is justified by Stage 1 checks.

Runtime commands after Stage 2 implementation:

```sh
./bin/dimmer
./bin/dimmer --stop
./bin/dimmer --kill
```

The direct fallback is `systemctl --user stop linux-custom-dimmer.service` for
the known dimmer unit. Routine recovery uses the identity-checking launcher.
