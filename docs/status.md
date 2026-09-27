# Project status

Updated: 2026-09-27.

## Current stage

Stage 1 is complete and ready for `build the app`. Independent review findings
are fixed and verified. Product UI is intentionally absent. No overlay was displayed.
The owner requires ordinary-account development and runtime with minimal
privileges. No sudo or system package installation was used.

## Local history

Branch: `stage-1-foundation`, in the requested project directory.

- `a5a8a67` — initial agreed scope and evidence.
- `35dadec` — rootless development environment, matching headers, native adapter.
- `68c22cf` — independent launch/recovery, unit identity checks, live process tests.
- `a8ccdec` — state contract, bounded unmapped probe, and Stage 1 handoff.
- `0812c8e` — final review fixes and failure-path regression tests.
- Final documentation commit follows `0812c8e`; use `git log --oneline -6`.

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

## Results and integration

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

The only persistent application-specific runtime files are private ownership and
lock files under `$XDG_RUNTIME_DIR/linux-custom-dimmer/`. Test runs create
similarly private directories named for their disposable units; this session
removed those after confirming their services were absent. Logout removes
runtime files. They are not processes or startup registrations.
No permanent application menu entry, shortcut, installed user unit, autostart,
or root service exists. The KDE test temporarily used
`~/.local/share/kglobalaccel/linux-custom-dimmer-stage1-probe.desktop` and removed
it. Final inventory confirms zero dimmer/test units and zero dimmer timers;
no dimmer, sentinel, or probe remains running.

Raw native diagnostics and setup output remain under ignored `.local/`.
See `docs/verification.md` for actual results and limitations, and
`docs/kde-integration.md` for the external shortcut mechanism.

## Remaining work and next action

Next instruction: `build the app`. That authorizes Stage 2 Tasks 4–6. Implement the Qt raster overlay and native controls, require
support/recovery preflight before activation, add lifecycle cleanup and show
IPC, and install the actual independent emergency shortcut/menu entry.
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
