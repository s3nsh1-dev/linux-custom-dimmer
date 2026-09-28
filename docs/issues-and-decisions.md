# Issues, evidence, and decisions

Keep this document useful to a new Codex session. Add a dated entry for each
significant problem or architecture change. Include the symptom, evidence,
cause or remaining uncertainty, chosen fix, verification, and commit when one
exists. Do not label an untested idea as a solution.

## 2026-09-27: accepted product and stack

The user confirmed that a neutral black overlay gives the desired dimming and
chose Python over TypeScript for this project. The target is a small native app,
one slider, Start/Stop, and dependable emergency recovery. Codex has authority
over architecture within the agreed scope. Public support for every Ubuntu
desktop is deferred; this laptop is the first target.

Python with PyQt6 already produced the accepted effect. TypeScript with
GJS/GTK/layer-shell was researched but not tested here. It would add a different
native stack and compatibility work without serving the current goal.

## 2026-09-27: hardware dimming did not visibly work

Symptom: the user saw no change from `kscreen-doctor` dimming, even though the
requested brightness value decreased. An initial reading of the requested
value alone led to an incorrect impression that the test succeeded.

Evidence: requested brightness changed from 618 to 186; `actual_brightness`
stayed at 3855. Both returned-state checks and user observation matter. This is
consistent with the display/driver not producing a further hardware reduction
at that setting; the exact firmware reason was not established.

Resolution: use an independent visual overlay. Do not repeat the failed
hardware control as the proposed implementation.

## 2026-09-27: accepted overlay preview

Python `/usr/bin/python3`, PyQt6 6.10.2, Qt 6.10.2, and LayerShellQt 6.6.4
were available on Ubuntu 26.04.1 with KDE Plasma 6.6.6, Wayland.

The preview used a full-display black Qt raster window, alpha 128/255, and
layer-shell's overlay layer. It anchored every edge, used exclusive zone -1,
disabled keyboard interactivity, and set Qt input-transparent/no-focus flags.
There was no capture of desktop pixels and no frame-update timer. The user
confirmed the 10-second result, saying it was exactly the desired effect.

The prototype reached LayerShellQt through C++ symbol names using ctypes.
That was sufficient for a disposable feasibility probe, but it is fragile for
a maintained application. Build a narrow adapter against public headers or use
a verified supported binding. Do not copy ABI-specific symbol names into the
finished app. Only the mechanism, not the disposable implementation, is accepted.

## 2026-09-27: resource measurements

| Run | Observation | Interpretation |
| --- | --- | --- |
| 50% overlay, 120 seconds | 7.49 W before, 8.39 W during, 7.59 W after | Background activity changed; the apparent 11% increase is not an isolated overlay cost. |
| 65% overlay, 120 seconds, user idle | 7.13 W before, 7.22 W during, 7.19 W after | About 0.06 W or 0.9% above the surrounding baseline, close to normal variation. |
| Night Light, 180 seconds, user idle | 7.40 W; 1.99% overall CPU; 2.21% integrated GPU busy | KDE reported Night Light ON at 1000K throughout, despite the original intention to turn it off. |

The quiet overlay run recorded one paint, no measurable process CPU ticks after
startup, about 53.4 MiB proportional process memory, and 176.4 MiB resident
memory including shared libraries. KWin resident memory rose by about 8 MiB.
The discrete GPU remained suspended and actual backlight stayed at 3855.

Measurements used battery `current_now * voltage_now`, about once per second,
and `/proc`/sysfs readings. The sampler ran in each phase. Hardware readings can
repeat; short observations are not independent proof of a precise battery-life
penalty. Night Light state was not recorded during the earlier overlay tests,
so no clean Night Light versus overlay efficiency comparison exists. Do not
claim this app saves battery or beats Night Light.

The first report generator tried to average unavailable KWin proportional
memory readings. Raw samples were intact. The report was regenerated and the
script changed to tolerate missing optional metrics. New measurement tools must
likewise preserve raw data and handle unavailable sensors.

The old raw test scripts/reports were saved under `/tmp`; they are disposable
and are not a project dependency. This document preserves the relevant facts.

## 2026-09-27: safety architecture decision

Decision: a single normal-user Qt app in a dedicated transient systemd user
service, with recovery launched outside the app when using the emergency
shortcut or emergency launcher. A button inside a frozen process cannot be the
only escape. Service-scoped termination avoids matching unrelated Python apps.

The existing user service manager was reachable and reported `degraded`.
No unrelated services were changed. Actual launch/kill isolation and the KDE
external shortcut mechanism remain Stage 1 validation work. This design has
not yet passed application recovery tests.

Decided against broad `pkill`, a permanent root daemon, automatic restart,
unrestricted dimming to full black, and an in-process shortcut as the sole
recovery mechanism. The extra launcher and small native adapter are justified
by reliable recovery and compatible native integration; keep their scope narrow.

## References for implementation

- [LayerShellQt public window interface](https://raw.githubusercontent.com/KDE/layer-shell-qt/master/src/interfaces/window.h) documents anchors, layer, keyboard interactivity, and per-window configuration.
- [Qt window flags](https://doc.qt.io/qt-6/qt.html#WindowType-enum) includes input transparency and focus flags. Validate behavior on the installed version.
- [systemd process termination](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html) describes service-scoped termination. Also read the installed `systemd.kill` and `systemd.service` manual pages during setup.
- [KDE idle dimming implementation](https://raw.githubusercontent.com/KDE/powerdevil/Plasma/6.6/daemon/actions/bundled/dimdisplay.cpp) requests a ratio of the current brightness; this is not proof of additional software dimming on this panel.

At the original documentation handoff, no app code, dependencies, desktop
integration, or Git repository had been created. Stage 1 work follows below.

## 2026-09-27: ordinary-account development and native headers

Symptom: CMake, Ninja, venv's ensurepip bundle, Qt development headers, and
LayerShellQt headers were absent. The runtime packages were already compatible.
The first proposal used system-wide APT installation, which needs an admin
account. `sudo -n true` was denied. No privileged install was attempted.

The user clarified that development and running must work in the ordinary
account, and requested the least privileges practical. This is now a project
requirement. Sharing/open-source distribution is undecided; keep Git local.

Fix: use existing distro pip through a `--system-site-packages --without-pip`
venv, with pinned developer tools inside it. Read installed runtime package
versions and use `apt-get download` plus `dpkg-deb -x` for matching headers
inside ignored `.local/`. No maintainer scripts or system installs run.
CMake links the three existing runtime libraries directly. It avoids Qt's
broader CMake package dependency checks for unused OpenGL/Vulkan/qmake tooling.
No copied Qt runtime or private C++ symbol lookup is used.

Verification: rootless setup and its repeat completed; the adapter compiled,
`ldd` resolved system libraries, and all 64 default tests passed. Future setup
after a system Qt update must download matching headers again; unavailable
archive versions fail explicitly. See the environment foundation commit in
`docs/status.md`.

## 2026-09-27: service identity and recovery proof

Decision: use distro dbus-python for typed systemd calls. A fixed executable
and argument list, a project-path digest, safety properties, and an owner-only
random token must all match. Reject absent/stale ownership for existing units.
Hold a manager unit reference while inspecting and signalling so the unit
cannot be garbage-collected and replaced under the same name. Serialize project
launchers with a bounded owner-only file lock. The CLI accepts no target override.

The system Python recovery CLI does not need Qt or a working venv. Only the
service app uses the venv. This minimizes recovery dependencies. A duplicate
Stage 1 launch reports Already running; showing an existing UI awaits Stage 2.

Verification: mocked-boundary safety tests plus real temporary services proved
collisions are refused, concurrent launches do not stack, frozen parent/child
cleanup works, and an unrelated sentinel survives. Stop 2.473s; kill 0.471s.
An independent systemd runtime limit also removed a frozen dummy. Existing
degraded services were left alone. Runtime test deadlines add no permanent daemon.
See the recovery foundation commit in `docs/status.md`.

## 2026-09-27: native compile and protocol-query corrections

The first native build rejected a plain bitwise OR of LayerShellQt anchor enums
because it produced an int. Use an explicit `Window::Anchors` value before
combining flags. The strict-warning build then passed.

The installed wayland-info pads columns, unlike the initial parser fixture.
The protocol preflight incorrectly rejected a supported compositor. Captured
its real output in a failing regression test, then accepted whitespace around
the protocol/version fields. Test and live preflight passed.

Native loading verifies bridge ABI and exact Qt compile/runtime versions. Python
holds the GIL and a live QWindow reference, rejects a deleted object or wrong
thread, and the C++ bridge repeats thread/platform/version checks. The bridge
retains no window pointer. Caller cleanup after later surface failures remains
part of the Stage 2 overlay controller. See the native foundation commit in status.

## 2026-09-27: KDE recovery route and unmapped probe

KDE command dispatch was proven through a temporary desktop action with no key
bound. Its independently launched command killed a frozen owned dummy in 0.213s
and left the sentinel alive. Removed the registration and file and verified
NoSuchComponent. Ctrl+Alt+Shift+D was free; recheck at Stage 2 installation.
Physical key delivery and permanent menu integration remain Stage 2 acceptance.

The native probe configured and created only unmapped windows, then destroyed
them. Its own timer and an independent systemd deadline bounded the experiment.
This avoided another visual preview during base setup. Do not infer input
transparency or layer stacking from this probe. Those need the actual rendered
app and live acceptance tests. Details are in `docs/verification.md`.

## 2026-09-27: final review and cleanup failure paths

Independent review found that the KDE test created its desktop entry before
entering cleanup protection. A setup exception could leave the file behind.
Sequential cleanup could also skip unregister/removal and sentinel cleanup if
service recovery raised. Fix: register cleanup as each resource is acquired,
using ExitStack and separate contexts. Unregister, file removal, cache refresh,
and sentinel cleanup now execute independently; error chains remain visible.
Failure-injection tests cover connect/body/unregister failures and file collisions.

Review also noticed that an identity-verified but inactive/failed/deactivating
unit reported Already running. Although graded minor by the reviewer, this
could conceal a failed launch from the owner. Treat it as a launch-correctness
issue: return a clear retry error without restarting the service. Three new
tests failed on the old behavior and passed after the change.

During the cleanup refactor, a live rerun caught the KDE service name being
used as its interface name. These differ in capitalization. Restored the
verified `org.kde.KGlobalAccel` interface. The failure itself confirmed that
desktop cleanup still ran. The final live suite passed all five cases, with
normal stop 2.315s, immediate kill 0.272s, and KDE recovery 0.127s. The final
default suite passed 72 tests. No review finding remains deferred. See the
review-fix commit in `docs/status.md`.

## 2026-09-27: Stage 2 rendering and first live checks

The overlay now uses QBackingStore and source-composition black with validated
alpha. Source composition replaces pixels, so repainting does not accumulate
darkness. Active state follows the first completed paint. An exposure deadline
fails closed if the compositor never exposes the surface. Static overlays have
no repeating timer; stop destroys the backing store and native surface.

The control window starts Stopped at 50%. Offscreen tests verify slider/start/
stop/zero/close/emergency transitions, invalid opacity, and failure cleanup.
The first bounded real-app probe passed at 50%, 65%, and 80%, with paint counts
1, 2, and 3 and no additional paints while idle. Zero removed the overlay.
The app had an inner quit timer and a 20-second systemd runtime deadline.

Two real-environment issues were caught before dimming. PyQt's dynamic QObject
property lookup returned None for PreparingForSleep; explicit D-Bus Properties.Get
returned the correct boolean. KDE accepted the shortcut key but left its action
inactive with NoAutoloading alone. Adding SetPresent activated it, verified by
querying both the assigned key and component state. Failed installs rolled back
their files and registration; unavailable checks left the app Stopped.

Only two owned files were installed under the user's applications directory:
linux-custom-dimmer.desktop and linux-custom-dimmer-emergency.desktop. The latter
also supplies the independent KDE command shortcut. No root access, extra daemon,
system unit, autostart or global shell integration was added. Physical key and
interaction acceptance, final lifecycle tests and resource measurements remain
in progress. See the Stage 2 commits in status.

## 2026-09-27: IPC validation and real application recovery

Adversarial requests with a list or object as `action` raised TypeError during
set membership instead of a protocol error. Two regression cases failed, then
passed after checking that the action is a string. Real Unix-socket tests also
cover multiple JSON frames, oversized requests, partial-client expiry, private
permissions and cleanup. The tool sandbox blocks socket creation (EPERM);
running the same safe tests with ordinary-user tool access passed. No sudo is
involved, and tests still use only their own temporary sockets.

Relaunch now sends a bounded, fixed `show` request after checking service
identity. A frozen or unresponsive instance produces a recovery instruction;
it never causes a second instance. The installed KDE shortcut route and actual
desktop-entry launch route killed the frozen real app in 0.256s and 0.588s.
The unrelated sentinel survived. SIGTERM, SIGKILL, quit, Stop and duplicate
launch tests passed, each with an external service deadline and app quit timer.
The fast 0.315s graceful stop is consistent with systemd continuing a stopped
process during shutdown, allowing the new event-driven signal wakeup to run.
This does not replace the separately proven immediate kill route.

## 2026-09-28: final review, registration ownership and probe expiry

The independent Stage 2 review found two important gaps and no critical or minor
findings. An uninstall with no desktop files could unregister a pre-existing
same-name KDE action; a failed repair could discard its previous key assignment.
The installer now requires the exact owned emergency file before mutating an
existing action, snapshots its keys/presence, and restores that snapshot on
failure. Cleanup is registered before desktop-cache refresh because KDE may
discover the new action during that refresh. Four regression scenarios failed
before the fixes and then passed: missing ownership on install/uninstall,
failed repair, and a cache failure after registration.

Live removal exposed two KDE details that the fake boundary had not modeled.
Unregister can leave an empty component behind. Snapshot now distinguishes an
empty component from a real unbound action by querying shortcutNames; the
latter still requires ownership evidence. Also, isGlobalShortcutAvailable
includes this component's own action in its current context. A repeat install
now returns after verifying exact files and the already-active assigned key;
repairing that owned key does not request a new reservation. New key assignments
still require availability. Regression and live remove/reinstall checks passed;
281 unrelated shortcut actions and two unrelated menu files were unchanged.
The [KDE component implementation](https://raw.githubusercontent.com/KDE/kglobalacceld/master/src/component.cpp)
confirms the current-context semantics. No broad shortcut-config rewrite is used.

The video measurement originally launched ffplay as a child of the sampler,
which did not protect it if the sampler or video event loop froze. It now has
its own precisely identified transient user service, a manager runtime deadline,
and ffplay's own playback deadline. A frozen disposable video process expired
independently in 0.994s without invoking sampler cleanup. Dimmer and video
cleanup run independently, and raw readings are retained even if cleanup fails.
No additional runtime dependency was installed: ffmpeg/ffplay were already present.

The first video sample was invalidated by changes from Stopped to 7/8% Active
and then app exit. Its partial readings were retained but excluded from resource
conclusions. The sampler now rejects a changed control/session state during a
phase. Neither that interaction nor command dispatch is treated as a substitute
for the owner's deferred hands-on acceptance.

One tool operation on September 27 was not executed because automatic approval
review hit its usage limit. Work resumed after the user changed tool permissions.
This was an agent-tool access issue; no app task required root or sudo.
