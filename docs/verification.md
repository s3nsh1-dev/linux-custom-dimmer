# Verification record

## Stage 2 implementation, 2026-09-27–28

Branch: `stage-2-app`. App checkpoint `0369a41`; review and integration fixes
`eb0907a`; minimized sampling/relaunch check `405708d`. Subsequent handoff edits
are documentation only. Version remains `0.1.0.dev0`; no release tag or remote.
The owner explicitly deferred hands-on acceptance. **Implementation and the
checks below are done; Stage 2 release acceptance remains incomplete.**

The Stage 1 environment below still applies. Stage 2 added no installed Python,
Qt, system package, or plugin dependency. Resource tests use the already installed
ffmpeg/ffplay. All application operations and installation ran as the ordinary
user; tool sandbox escapes did not grant or require root privileges.

### Automated and live evidence

- `scripts/check`: native build, matching Qt imports, compilation, Ruff and
  formatting passed; 128 safe tests passed, 14 live cases deselected.
- The full explicitly enabled suite passed 140 cases at the review-fix revision.
  The later minimize protocol and UI cases passed in the 128-case safe suite;
  its live relaunch test also passed. The unchanged live paths retain the
  preceding suite evidence; no physical-input result is inferred from it.
- Offscreen controls cover Stopped launch at 50%, active/stopped slider changes,
  integer cap, zero-stop, repeated transitions, failure cleanup, close, emergency
  quit, minimized-state retention and restoring the same window.
- Real Unix sockets cover private permissions, fixed actions, invalid action
  types/numbers, repeated JSON fields, multiple frames, size limits, idle-client
  expiry and cleanup. The recovery CLI never depends on this socket or on Qt.
- Injected lock, suspend, geometry/topology and service-disconnect notifications
  removed the owned surface and did not restart it. Actual session transitions
  are among the outstanding hands-on checks.
- The real app rendered 50/65/80% and returned Stopped at 0%. Paint counts were
  1/2/3 after the three changes with no additional idle paint. Separate real-app
  checks cover Start/Stop/Start, duplicate launch, minimized relaunch, quit,
  SIGTERM and SIGKILL. Each test had its own app quit timer and an independent
  systemd expiry. No test service remained afterward.

Live test commands (close an existing dimmer first):

```sh
DIMMER_LIVE_TESTS=1 DIMMER_KDE_TESTS=1 DIMMER_APP_TESTS=1 \
DIMMER_INSTALL_TESTS=1 DIMMER_VIDEO_TESTS=1 \
.venv/bin/python3 -m pytest -q -s
```

Raw output is ignored in `.local/final-tests.log`. Earlier isolated test commands
are in README. The opt-in tests never target KWin, Plasma or another real app.

| Recovery case | Initial Stage 2 | Review-fix retest | Result |
| --- | ---: | ---: | --- |
| Frozen real app, KDE emergency command dispatch | 0.256s | 0.156s | Owned process gone; sentinel survived |
| Frozen real app, installed emergency desktop via `kioclient exec` | 0.588s | 0.204s | Owned process gone; sentinel survived |
| Frozen real app, independent graceful stop | 0.315s | 0.215s | Owned process gone; sentinel survived |
| Frozen SIGTERM-ignoring dummy and child, stop | Stage 1 below | 2.248s | Two-second escalation works; sentinel survived |
| Frozen dummy and child, immediate kill | Stage 1 below | 0.232s | Sentinel survived |
| Frozen dummy, temporary KDE command route | Stage 1 below | 0.105s | Sentinel survived; test registration removed |
| Frozen video probe, independent expiry | 0.994s | 1.042s | Exited without sampler cleanup |

The immediate paths met the <1s target and graceful fallback met <3s. Physical
keyboard delivery is distinct from invoking KDE's command route and remains
unverified. Process/surface lifetime evidence is distinct from a human confirming
visible restoration.

Installation/removal/reinstallation passed with the live user account. Uninstall
stopped the app first; both desktop files and the `_launch` action were removed;
a repeat uninstall was harmless; install and repeat install then passed.
All 281 unrelated shortcut actions and both unrelated user desktop entries were
unchanged. `desktop-file-validate` accepted both owned entries. Exact external
paths and the registration mechanism are in README and `docs/kde-integration.md`.

### Resource method and observed limits

The sampler ran for every OFF/ON/OFF phase, with 65% opacity during ON and one
sample every five seconds. Each phase lasted 60 seconds, after startup and
transition warm-up. The default reproducible command supports 180-second phases;
these shorter development comparisons establish application idle cost but are
insufficient for battery-life claims. Desktop activity was not fully quiescent.
Application CPU and KWin CPU are separate, as percent of one core from `/proc`
ticks. Memory is mean RSS/PSS from `smaps_rollup` where readable. Hardware sensors
were read only. No GPU diagnostic was launched to wake a sleeping device.

```sh
scripts/measure-resources --seconds 60 --workload idle
scripts/measure-resources --seconds 60 --workload video
```

The idle run used `0369a41`, display eDP-1 at 1920×1080, 60 Hz, scale 1, battery
27% discharging, AC disconnected. Backlight requested 1, actual 3855, maximum
61680. Night Light disabled/not running, current 6500K, target 1000K. These
settings were unchanged within the comparison. Later runs occurred after a new
login and used their own fresh baseline; do not compare across those settings.

| Idle phase, 60s | App CPU | App RSS MiB | App PSS MiB | KWin CPU | Battery W mean (range) |
| --- | ---: | ---: | ---: | ---: | ---: |
| OFF before | 0.033% | 187.49 | 58.36 | 6.500% | 14.278 (13.430–15.060) |
| ON 65% | 0.017% | 196.46 | 63.13 | 6.167% | 15.131 (14.647–15.476) |
| OFF after | 0.017% | 188.56 | 59.18 | 3.717% | 13.302 (10.660–14.513) |

ON paint count remained 1. App CPU and PSS were below the investigation thresholds
(0.2% and 100 MiB). KWin memory was unreadable for this user and is not inferred
from application RSS. The Nvidia device remained runtime-suspended in all
samples. AMD integrated-GPU busy readings were available; the changing desktop
and falling OFF-after compositor activity make overlay-only GPU/power attribution
inconclusive. Battery estimates use current×voltage; repeated readings are not
independent samples. No battery saving or precise overlay power penalty is claimed.

Raw idle data: `.local/resources-idle-20260927-192151.json`.
Several video attempts were invalidated by manual control changes/app closure;
they are retained as partial logs and excluded. The sampler now checks that its
expected state remains unchanged, minimizes the controls, and puts both the app
and video workload in independently expiring services. Video uses a generated
1280×720 MPEG4 clip at 30fps, looping in a 960×540 software-decoded ffplay window.

The completed video run used `405708d` on AC with battery 100%/Full, display
1920×1080 at 60 Hz, Night Light disabled/not running, current 6500K and target
2000K. The power profile read immediately afterward was `power-saver`; it was
not sampled through the phases. Raw data is
`.local/resources-video-20260928-191233.json`; summary/diagnostic output is
`.local/video-measurement.log`.

| Video phase, 60s | App CPU | App RSS MiB | App PSS MiB | KWin CPU | AMD busy mean (range) |
| --- | ---: | ---: | ---: | ---: | ---: |
| OFF before | 0.167% | 187.96 | 63.33 | 15.500% | 12.85% (9–21%) |
| ON 65% | 0.017% | 196.44 | 67.87 | 12.583% | 10.15% (9–11%) |
| OFF after | 0.000% | 188.54 | 63.92 | 10.783% | 13.38% (10–15%) |

All three app states stayed correct, with ON paint count fixed at 1 and the
Nvidia device suspended throughout. However, at 35 seconds in the first OFF
phase the requested backlight changed 618→61680 and actual backlight 3855→50780.
This happened before any overlay was created. Night Light values stayed fixed.
The sampler finished all phases and cleanup, then its final settings assertion
correctly failed. The change's source was not established; neither the app nor
sampler contains a backlight write. It was not rewritten as a supposed restore.

Thus application CPU/memory/paint observations are usable, but the complete
controlled video comparison **did not pass** and power attribution is
inconclusive. The battery's zero current while full/on AC is not zero system
power. Compositor/GPU activity also varied. Repeat under fixed desktop brightness
if a stronger comparison is needed; do not claim efficiency from these numbers.

### Remaining acceptance and next check

The owner selected “Continue; I can test later.” Keep these open:

1. Confirm visible neutral dimming at 50/65%, zero removal, actual text/pointer/
   scroll and available touch passing, popup/modal and fullscreen interaction.
2. Press Ctrl+Alt+Shift+D with another app focused, while minimized, and with the
   verified dimmer frozen. Arm an independent short deadline before the frozen
   test. Command-route tests already pass but do not prove physical key delivery.
3. Check actual lock/unlock, suspend/resume and display changes, including no
   automatic restart of dimming. Injected handlers and live preflight pass.
4. Confirm visible cleanup on close/crash/recovery and unchanged desktop settings
   during those hands-on tests.

Use a bounded session for acceptance with an internal timer and external service
expiry. Do not disrupt other work by deliberately locking/suspending without
coordinating the test. Routine use starts with `./bin/dimmer`; independent immediate
recovery is `./bin/dimmer --kill`. No `v0.1.0` tag is justified until acceptance passes.

## Stage 1 verification (historical)

Date: 2026-09-27. Branch: `stage-1-foundation`. Final tested code: `0812c8e`, with later documentation-only completion.
Earlier checkpoints are listed in `docs/status.md`; this file records observations, not Stage 2 acceptance.

### Environment and installs

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

### Commands and observed results

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

### Failure and retest history

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

### Limits of this stage

No finished control UI, visible dimming, actual key-press test, click-through
acceptance, lock/suspend/topology handling, or final resource measurement exists
in Stage 1. The native probe establishes loading, configuration, native window
creation and cleanup; it does not establish compositor stacking or input behavior.
No permanent desktop integration, root service, autostart entry, plugin, remote,
release tag, or publication was created. Stage 2 must prove its visible behavior
and emergency key using the real app before any release claim.

## Final cleanup inventory, 2026-09-28

`bin/dimmer --kill` reported Already stopped. `systemctl --user list-units --all
'linux-custom-dimmer*'` listed zero units; matching list-timers listed zero timers.
The process inventory found no dimmer app, video, measurement sampler, dummy or
sentinel. The two exact owned desktop files and the active emergency registration
were re-verified and remain installed for normal use. Private runtime records
may remain until logout; they are not processes or startup registrations.
