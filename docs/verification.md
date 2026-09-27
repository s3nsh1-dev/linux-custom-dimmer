# Stage 1 verification

Date: 2026-09-27. Branch: `stage-1-foundation`. Final tested code: `0812c8e`, with later documentation-only completion.
Earlier checkpoints are listed in `docs/status.md`; this file records observations, not Stage 2 acceptance.

## Environment and installs

Ubuntu 26.04.1, KDE Plasma 6.6.6, Wayland. Python 3.14.4, PyQt6 6.10.2,
Qt compile/runtime 6.10.2, LayerShellQt 6.6.4, dbus-python 1.4.0,
GCC 15.2.0, systemd 259.5. The graphical session target was active.
The user manager reported degraded; the required service operations worked.

No sudo or system package installation was performed. Added only inside the
project: `.venv` with system packages visible; pytest 9.0.2, Ruff 0.15.7,
setuptools 82.0.1, iniconfig 2.3.0, pluggy 1.6.0, CMake 4.2.3, Ninja 1.13.0,
and this package editable at `0.1.0.dev0`.
Ubuntu's pre-existing pip 25.1.1, packaging 26.0 and Pygments 2.19.2 are visible
through system packages. Existing Qt, PyQt6, compiler, and dbus packages were
unchanged. No Qt package was installed from pip.

Downloaded `qt6-base-dev=6.10.2+dfsg-7` and
`liblayershellqtinterface-dev=6.6.4-0ubuntu1` using APT into `.local/debs`.
`dpkg-deb -x` extracted them into `.local/sysroot`. Versions exactly match the
installed runtime packages; `.local/sysroot/versions.json` records the mapping.
`ldd build/native/libdimmer_layer_shell.so` resolves QtCore, QtGui, and
LayerShellQt to `/usr/lib/x86_64-linux-gnu/`, with no missing dependencies.
`nm -D --defined-only` shows only the four intended unmangled bridge exports.

## Commands and observed results

| Command/check | Observation |
| --- | --- |
| `scripts/setup-dev` | Rootless setup, editable installation and full checks passed; repeat run passed. |
| `scripts/check` | Final native build, matching Qt import, bytecode compilation, Ruff and formatting passed; 72 tests passed, 5 opt-in live cases deselected. |
| `DIMMER_LIVE_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_recovery.py` | 4 passed. Frozen dummy and its child removed; independent sentinel survived with unchanged PID/start time. Concurrent launch yielded one service; wrong identity refused. External runtime deadline terminated frozen dummy. |
| Frozen dummy normal stop | Initial 2.473 seconds; final retest 2.315 seconds. Target below 3 seconds. Dummy ignores SIGTERM, exercising escalation. |
| Frozen dummy immediate kill | Initial 0.471 seconds; final retest 0.272 seconds including a separate Python recovery process. Target below 1 second. |
| `DIMMER_KDE_TESTS=1 .venv/bin/python3 -m pytest -q -s tests/integration/test_kde_route.py` | Passed initially and after review fixes. Initial KDE recovery 0.213 seconds, final 0.127 seconds. Sentinel survived. |
| Shortcut availability | `Ctrl+Alt+Shift+D` available at check time. Probe bound no key. |
| `scripts/probe-native` | Success, 516 ms service lifetime. GUI-thread adapter configured an unmapped QWindow, rejected configuring it after native creation, and destroyed both probe windows. No pixels drawn. |
| Native probe deadline | Qt timer 250 ms; systemd RuntimeMaxSec=5 plus TimeoutStopSec=1, outside Qt process group. Service completed normally before deadline. |
| `bin/dimmer --stop`, `bin/dimmer` | Missing service is harmless; launch starts the Stage 1 stub which exits with no window. A later unit inventory reported zero dimmer units. |
| KDE cleanup | Temporary desktop file removed; `getComponent` returned `NoSuchComponent`. No permanent binding created. |

Automated cases cover malformed CLI arguments, unit collisions, stale/missing
owner records, private-file symlink/permission rejection, space-containing paths,
state transitions/invalid numbers, missing bridge, runtime Qt mismatch,
wrong GUI thread, deleted windows, offscreen rejection, unsupported desktop,
missing layer protocol, bounded protocol query and real wayland-info spacing.
Default tests never connect to the live desktop or signal services.

## Failure and retest history

- System build dependencies were absent and passwordless sudo was unavailable.
  The user needs ordinary-account development. Switched to pinned venv build
  tools and exact-version distro header extraction. Build and setup repeat passed.
- The first C++ compile rejected OR-ed anchor enums as an integer. Explicitly
  construct `LayerShellQt::Window::Anchors` before combining flags. Build passed
  with `-Wall -Wextra -Wpedantic -Werror`.
- The first layer-protocol parser assumed one space, but installed wayland-info
  pads columns. A regression test failed, then passed after accepting whitespace.
- New behavior tests initially failed because their modules did not yet exist;
  implementation and subsequent complete checks passed. No failed check was
  treated as success.
- Independent review identified failure-path cleanup and stale-unit reporting
  issues. Added eight regression cases and fixed both. A live refactor retest
  caught an incorrect KDE interface spelling; corrected it, then all five
  opt-in tests passed together. The temporary desktop file was removed even
  during the failed run. Final `scripts/check`: 72 passed. Plain `pytest`: 72
  passed, 5 explicitly skipped live cases. Review fixes are separately committed.

## Limits of this stage

No finished control UI, visible dimming, actual key-press test, click-through
acceptance, lock/suspend/topology handling, or final resource measurement exists
in Stage 1. The native probe establishes loading, configuration, native window
creation and cleanup; it does not establish compositor stacking or input behavior.
No permanent desktop integration, root service, autostart entry, plugin, remote,
release tag, or publication was created. Stage 2 must prove its visible behavior
and emergency key using the real app before any release claim.
