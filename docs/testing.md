# Testing and release acceptance

This is the test plan, not a claim that these tests have passed. Run it against
the implemented app and record results in `docs/verification.md`.

## Automated checks during development

Use pytest for meaningful behavior tests and Ruff for static checks. Test pure
state and command construction without requiring a display. Use Qt's testing
support for controls and injected lifecycle notifications. Do not add tests
that merely mirror getters, constants, or third-party framework behavior.

`scripts/check` must build the native adapter, verify imports, run static
checks, and run the non-destructive tests. It must not activate dimming, capture
the user's desktop, or signal live applications. Live tests must be explicitly
selected and labelled, with their own bounded cleanup.

| Area | Required cases | Evidence |
| --- | --- | --- |
| Opacity/state | 0, 1, 50, 65, 80; negative and above-limit input; strings and non-finite numbers; Start/Stop/Start; idempotent Stop | Correct state and surface requests; no invalid value can become a full-black overlay. |
| Controls | Launch Stopped; stopped slider adjustment; active adjustment; keyboard access; close window | Native UI actions cause the specified state transitions and cleanup. |
| Native integration | Missing library, Qt mismatch, wrong thread, absent layer-shell support, surface creation failure | Clear error, no visible layer, and no orphaned resource. |
| Recovery boundary | Wrong unit identity; missing unit; stale ownership information; path with spaces; malformed CLI/IPC; arbitrary PID/unit attempt | No action reaches an unrelated unit or executes input as shell code. |
| Lifecycle | Inject lock, suspend, geometry, output removal, and compositor disconnection | Every owned overlay disappears and the state remains Stopped. |
| Single instance | Concurrent launches; relaunch while active; IPC timeout | One instance and one overlay at most; no silent fallback to an unsafe launch. |
| Rendering | Repeated identical opacity; idle period; Stop then resize notification | No continuous repainting, unintended layer recreation, or retained paint timer. |

Write regression tests when a discovered bug changes expected behavior. Include
the failing condition, not just the eventual implementation. Prefer explicit
failure assertions over a coverage percentage that hides missing safety cases.

## Real process isolation and frozen-app recovery

First prove lifecycle control using disposable test programs, before darkening
the display. Start the owned dummy in a dedicated test service and a separate
unrelated sentinel. Verify graceful stop and forced termination target only the
owned service. Confirm the sentinel's PID/start time and continued operation
before and after. Stop the sentinel through its own normal cleanup afterward.

Repeat recovery with the real dimmer. Before freezing it, arm an independent
short deadline outside its process group that invokes its recovery command.
Use SIGSTOP only on the known owned dimmer process. Exercise the actual external
emergency shortcut and launcher. Success means the dimmer exits and its layer
disappears while the sentinel remains alive. A graceful quit of an unfrozen app
does not satisfy this test.

Record recovery latency. Target visible restoration within one second for the
immediate kill path, and within three seconds for the two-second graceful-stop
timeout plus dispatch overhead on an otherwise responsive desktop. Investigate
misses; do not change the target after seeing a failure without documenting why.

Do not freeze, kill, restart, or alter real unrelated applications, Plasma,
KWin, the shell, power services, or the user's current login session. Never
use broad process matching. Verify cleanup even when the test itself fails.

## Live KDE behavior

Check all of the following on the supported laptop before declaring completion:

- Neutral dimming is visible at 50% and 65%, and 0% removes it.
- Text entry, pointer clicks, wheel scrolling, and available touch input reach
  the intended application under the layer. Fullscreen windows and popups work.
- The normal control window remains usable. The external emergency shortcut
  works when another app has focus, when the dimmer is minimized, and when it
  is frozen. The emergency launcher uses the same independent recovery path.
- Hardware brightness, actual backlight, Night Light, and power settings match
  the initial recorded values after each test. Read settings; do not rewrite
  them as a supposed restoration step.
- Closing, crashing, and terminating the app remove the layer. Repeated launches
  cannot stack layers. Lock/suspend/display changes return it to Stopped.
- Installation and uninstallation affect only documented app-owned files and
  registrations. Uninstall stops the app first and leaves other shortcuts intact.

An offscreen Qt test cannot prove layer-shell stacking, actual click-through,
or a global shortcut. Use live evidence for those claims. Do not treat an
unperformed manual check as passed. Avoid unattended full-black experiments.

## Resource measurement

Use the finished app, with its normal launch/recovery route. Record versions,
opacity, display resolution/refresh rate, power source, battery status,
backlight, Night Light running state/temperature, and foreground workload.
Measure application CPU, proportional and resident memory, compositor CPU,
integrated GPU activity, and discrete GPU sleep state when sensors are available.

Use comparable OFF/ON/OFF periods, ideally at least three minutes each after
warm-up. Keep ordinary activity constant and separate idle results from video
results. Do not launch a GPU diagnostic that wakes a sleeping discrete GPU.
The resource sampler must run in every comparison phase. Preserve raw readings
outside Git and commit the method and summary, including variation and missing
sensors. Repeated battery readings are not independent evidence.

Compare with the prototype as a reference, not a guarantee. Investigate CPU
above 0.2% of one core at idle or proportional app memory above 100 MiB.
Measure application and compositor costs separately. Do not equate resident
memory including shared libraries with exclusive memory, or claim exact battery
life from a brief power sample. No comparison with Night Light is valid unless
its state is recorded and the other conditions are controlled.

## Release record

`docs/verification.md` must identify the tested code revision, environment,
commands, results, failure/retest history, live checks, recovery latency,
resource summary, and remaining limitations. Required safety or live behavior
checks cannot be waived merely because unit tests pass. Tag `v0.1.0` only after
the required checks pass. End testing with no active overlay or test process.
