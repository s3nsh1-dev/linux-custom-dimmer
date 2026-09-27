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

No app code, dependencies, desktop integration, or Git repository has been
created by this documentation step. There are no implementation commits yet.
