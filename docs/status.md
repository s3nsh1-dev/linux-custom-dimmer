# Project status

Updated: 2026-09-28. Branch: `stage-2-app`.

## Current stage

Stage 1 is complete. Stage 2 is implemented and installed for the current user;
release acceptance remains open because the owner explicitly deferred hands-on
input, physical shortcut and actual session-transition checks. Version stays
`0.1.0.dev0`. Do not call Stage 2 release-complete or tag `v0.1.0` yet.

The app opens Stopped at 50%, applies a neutral layer on Start, accepts 0–80%,
stops at zero, and cleans up on Stop/close/quit. Relaunch restores one existing
window. Independent identity-checked service recovery works with the GUI frozen.
Lock/suspend/output notifications stop dimming and do not restart it.

The owner requires ordinary-account development, installation and use with
minimal privileges. No sudo or system package installation was used. Tool
sandbox permissions concern the agent's access to the desktop and local sockets;
the application itself runs with ordinary user privileges.

## Saved checkpoints

- `ff28a31` — completed Stage 1 foundation and verification handoff.
- `ba108e0` — native overlay and controls, state/rendering/UI tests.
- `0369a41` — lifecycle guards, owner-only IPC, local launch/install/recovery.
- `eb0907a` — review fixes for shortcut ownership/rollback and video expiry.
- `405708d` — minimize controls during resource sampling, restore on relaunch.
- Final documentation/evidence commit follows those checkpoints; see `git log`.

Earlier Stage 1 commits: `a5a8a67`, `35dadec`, `68c22cf`, `a8ccdec`, `0812c8e`.
No remote, push, publication, merge, or release tag was created. Open-source
publication remains the owner's decision. All build and profiling output is ignored.

## Reproduce and use

```sh
./scripts/setup-dev
./scripts/check
./scripts/install-local
./bin/dimmer
./bin/dimmer --stop
./bin/dimmer --kill
```

Use **Linux Custom Dimmer** in the application menu. The independent emergency
key is **Ctrl+Alt+Shift+D**, and the separate menu entry is **Dimmer emergency
stop**. Both use the same Qt-independent `bin/dimmer --kill`. KDE command dispatch
and the actual desktop-entry route were verified against a frozen real app.
Physical key delivery is still pending. Direct fallback for the known unit:
`systemctl --user stop linux-custom-dimmer.service`.

Remove the integration with `./scripts/uninstall-local` before moving/deleting
this checkout. It stops the verified application first, then removes only owned
entries and the owned shortcut action. Repeat install and uninstall are safe.

## Dependencies and external integration

Observed environment: Ubuntu 26.04.1, Plasma 6.6.6, Wayland, Python 3.14.4,
PyQt6/Qt 6.10.2, LayerShellQt 6.6.4, dbus-python 1.4.0, GCC 15.2.0,
systemd 259.5. The existing system runtimes are unchanged.

Stage 1 created `.venv` with distro packages visible, pinned pytest 9.0.2,
Ruff 0.15.7, setuptools 82.0.1, iniconfig 2.3.0, pluggy 1.6.0, CMake 4.2.3
and Ninja 1.13.0. Matching headers were downloaded/extracted to `.local/sysroot`,
not installed into the OS. Re-run setup after Qt updates; never pip-install a
second Qt runtime. Stage 2 added no dependency; video tests use existing ffmpeg/ffplay.

Persistent integration is exactly these two user files:

- `~/.local/share/applications/linux-custom-dimmer.desktop`
- `~/.local/share/applications/linux-custom-dimmer-emergency.desktop`

With custom XDG_DATA_HOME the same relative `applications/` paths are used.
KDE owns the corresponding `linux-custom-dimmer-emergency.desktop` component
in its shortcut configuration/state, managed through its D-Bus API. No system
service, permanent user service file, autostart, plugin or extra daemon exists.

At runtime, `$XDG_RUNTIME_DIR/linux-custom-dimmer/` is mode 0700, with private
ownership/lock files and a mode-0600 control socket. A crash may leave a stale
socket pathname; the next verified app process replaces it. These are not
running processes. Logout removes runtime files. Resource/live tests create
similarly private directories for their disposable services; cleanup is recorded
in verification. All actual services are transient and have no automatic restart.

## Verification and limitations

- `scripts/check`: adapter build, imports, compilation, Ruff and format passed;
  128 safe tests passed, 14 opt-in live cases deselected.
- The full live-enabled suite passed 140 tests at the review-fix revision; the
  minimize addition then passed its safe tests and real-app relaunch check.
  Verification identifies these revisions separately; the safe suite and the
  changed live path were rerun after the minimize addition.
- Real app recovery retest: frozen KDE command 0.156s, emergency desktop route
  0.204s, graceful stop 0.215s. Frozen SIGTERM-ignoring dummy/child: stop 2.248s,
  immediate kill 0.232s. Unrelated sentinel survived. Frozen video deadline 1.042s.
- Live install/remove/reinstall preserved 281 unrelated shortcut actions and
  both unrelated user menu entries. Owned desktop files passed validation.
- The 60-second idle ON sample used 0.017% of one CPU core, 63.13 MiB PSS and
  196.46 MiB RSS, with one paint and no idle repaint. Battery/GPU cost cannot be
  isolated from background activity. Video ON used 0.017% CPU and 67.87 MiB PSS;
  its full comparison failed the final settings check because backlight changed
  during the initial OFF phase. No settings were rewritten. See verification.
- Independent review found two important gaps, both fixed and tested. Live
  retests also fixed empty KDE components and repeat-install availability
  semantics. No review finding remains deferred.

See [verification](verification.md) for commands, raw-log locations, resource
conditions, failure/retest history and acceptance limits. [Issues and decisions](issues-and-decisions.md)
records significant problems and reasons for implementation choices.

## Next executable step

Run `./bin/dimmer` for normal use, or ask to run the bounded hands-on acceptance
session when ready. Confirm neutral appearance and click/type/scroll/popup/
fullscreen behavior; test the physical emergency key with normal, minimized
and frozen app states; then test actual lock/suspend/display transitions.
These checks remain required before the release version/tag. A controlled video
comparison with fixed brightness also remains useful; the completed run was
inconclusive for power. Final inventory found no dimmer, video probe, sentinel
or timer running; the desktop integration remains installed.
