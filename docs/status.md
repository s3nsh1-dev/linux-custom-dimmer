# Project status

Updated: 2026-09-27.

## Current stage

Stage 1 implementation and checks passed; final review and documentation commit
are in progress. Product UI is intentionally absent. No overlay was displayed.
The owner requires ordinary-account development and runtime with minimal
privileges. No sudo or system package installation was used.

## Local history

Branch: `stage-1-foundation`, in the requested project directory.

- `a5a8a67` — initial agreed scope and evidence.
- `35dadec` — rootless development environment, matching headers, native adapter.
- `68c22cf` — independent launch/recovery, unit identity checks, live process tests.
- State contract and Stage 1 handoff are awaiting their final local commit.

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
  Python compilation, Ruff, formatting, and 64 default tests passed.
- Four live service tests passed. Frozen dummy plus child stopped in 2.473s;
  independent kill took 0.471s. Unrelated sentinel survived. Concurrency,
  wrong-identity refusal, and automatic external deadline were verified.
- KDE command test passed in 0.213s. Ctrl+Alt+Shift+D was available, but no key
  was bound. Temporary desktop file and registration were removed.
- Native probe succeeded in 516ms with only unmapped windows. It had a Qt timer
  and an independent systemd deadline. No pixels or dimming were displayed.
- The main Stage 1 service entry point prints an explanatory line and exits.
  `bin/dimmer --stop` and `--kill` are independent of Qt and the venv.

The only persistent application-specific runtime files are private ownership and
lock files under `$XDG_RUNTIME_DIR/linux-custom-dimmer/`. Test runs also create
similarly private directories named for their disposable units. Logout removes
runtime files. They are not processes or startup registrations.
No permanent application menu entry, shortcut, installed user unit, autostart,
or root service exists. The KDE test temporarily used
`~/.local/share/kglobalaccel/linux-custom-dimmer-stage1-probe.desktop` and removed
it. All current units were confirmed absent after the smoke test.

Raw native diagnostics and setup output remain under ignored `.local/`.
See `docs/verification.md` for actual results and limitations, and
`docs/kde-integration.md` for the external shortcut mechanism.

## Remaining work and next action

Finish final review and commit this handoff. Then `build the app` authorizes
Stage 2 Tasks 4–6. Implement the Qt raster overlay and native controls, require
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
