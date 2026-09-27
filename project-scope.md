# Linux custom dimmer: project scope

Date: 2026-09-27. Status: approved product direction; implementation has not started.

Build a small Python desktop app that makes this laptop's screen visibly darker
than the normal brightness slider can, without adding a red or yellow tint.
The user has tried the overlay described below and confirmed that it is exactly
the desired effect. Codex has authority to make the remaining architecture and
implementation decisions within this scope.

## What we are building

A plain native window with one slider, Start, Stop, and a prominent
**Emergency stop and quit** button. No accounts, network service, dashboard,
animations, or browser engine. The app should be easy to launch and remove.

The slider controls a transparent black layer above the desktop. Increasing
opacity makes the image darker; decreasing it makes the image lighter relative
to the current system brightness. It cannot brighten the screen beyond the
normal, uncovered image.

Initial support is this laptop: Ubuntu 26.04.1, KDE Plasma 6.6.6, Wayland, and
the built-in display currently named `eDP-1`. Discover the display at runtime;
do not make that connector name a universal assumption. GNOME, X11, other Linux
desktops, multiple monitor controls, and public distribution packages are later
work. Detect an unsupported session and explain it without applying an overlay.

## How we reached this design

The user wanted the dim appearance seen during idle or low-battery operation.
The clearer reference was Night Light at 1000K, but without its reddish tint.

`kscreen-doctor ... dimming.30` changed the requested backlight value from 618
to 186, but the driver's `actual_brightness` stayed at 3855. The user saw no
difference. Do not build a wrapper around that command or around the taskbar's
brightness control.

A temporary Python/PyQt6 preview instead drew a black layer with alpha 128/255
over the entire laptop screen. It used KDE's LayerShellQt library, did not take
keyboard focus, and allowed mouse input to pass through. It disappeared after
10 seconds. The user explicitly confirmed this effect. A subsequent preview
at alpha 166/255, approximately 65% opacity, also ran successfully.

The prototype used `QWindow`, an alpha-enabled surface, `QBackingStore`, and
`QPainter`. Its layer-shell configuration was overlay layer, all four edges
anchored, exclusive zone -1, and keyboard interactivity NONE. Qt's window flags
included `WindowTransparentForInput` and `WindowDoesNotAcceptFocus`. It painted
once and relied on compositor blending, with no screen capture or rendering
loop. These are implementation facts to preserve, not permission to ship the
prototype's direct calls to private C++ symbol names.

## Chosen stack and architecture

Use Python 3, PyQt6, Qt Widgets for the control window, and a Qt raster window
with LayerShellQt for the overlay. Use Ubuntu's compatible Qt/PyQt6/layer-shell
packages, not a second pip-bundled Qt runtime. Development tools can live in a
project `.venv` created with access to the distro's Python packages.

The application code should be Python. If no supported Python binding exposes
the needed LayerShellQt calls, use one small C++ adapter built against the
installed Qt6 and LayerShellQt headers. Expose a narrow C interface and load
that project-built library from Python. Keep it limited to configuring the
app's own live `QWindow`. Check errors, object lifetime, and GUI-thread use.
Do not retain hard-coded mangled C++ symbols, replace system libraries, or mix
Qt versions. Document the adapter as an interoperability detail; it is not a
second application or service.

Prefer one application process. The control window is a normal interactive
window; only the overlay is a layer-shell window. Do not globally force every
Qt window into layer-shell mode. Keep rendering, UI state, and recovery code
small and separate. A static overlay must not poll the screen or repaint on a
timer. Repaint only on exposure, geometry changes, and actual slider changes.

Run the application in a dedicated transient **systemd user service**, named
`linux-custom-dimmer.service`. This uses the existing user service manager,
not a new daemon, root service, or autostart entry. Give it `Restart=no`,
`KillMode=control-group`, `TimeoutStopSec=2s`, and `SendSIGKILL=yes`. Bind its
lifetime to the graphical session where supported. Pass only the display and
runtime environment it needs. Normal launch and recovery use project launchers.

This dedicated service gives an external recovery command a precise target.
It also allows a frozen app to be terminated without asking that app's event
loop to cooperate. A user manager reporting `degraded` is not by itself proof
that a new service cannot run; validate the required operations specifically.
Do not repair or restart unrelated user services.

## UI and state rules

| Action                                    | Required behavior                                                                |
| ----------------------------------------- | -------------------------------------------------------------------------------- |
| Launch                                    | Open in Stopped state. No overlay. Initial slider value 50%.                     |
| Slider                                    | Integer opacity from 0% to 80%, labelled Extra dimming. Higher means darker.     |
| Start                                     | Apply the selected opacity to the built-in display, after recovery checks pass.  |
| Adjust while active                       | Update the visible overlay promptly, without changing hardware brightness.       |
| Set 0%                                    | Remove the overlay and return to Stopped state.                                  |
| Adjust while stopped                      | Select the next opacity; do not start dimming implicitly.                        |
| Stop                                      | Remove the overlay immediately; keep the control window open.                    |
| Emergency stop and quit                   | Remove the layer and terminate this app. No confirmation dialog.                 |
| Close window or quit                      | Remove every owned overlay and exit; no hidden background operation.             |
| Minimize                                  | May retain an active overlay; the external emergency shortcut must still work.   |
| Relaunch                                  | Show the existing instance, or start one Stopped instance. Never stack overlays. |
| Lock, suspend, or display topology change | Remove the overlay and remain Stopped on return.                                 |

The 80% cap is a safety limit, not a guarantee that text will remain readable in
every environment. Match darkness by eye. An opacity percentage is not a
calibrated physical brightness percentage. The overlay adds no tint of its own
and does not cancel a Night Light tint that the user has enabled separately.

Keep the window compact, with native widgets, readable labels, keyboard access,
and a clear Active/Stopped status. The control window may also appear dimmer
because it is underneath the overlay. Recovery must therefore also work without
finding or reading that window. No tray integration is required for version 1.

## Safety and recovery are release requirements

1. Run as the current user. No root privileges, kernel changes, gamma-table
   writes, ICC changes, brightness writes, Night Light changes, power-profile
   changes, or compositor restarts during normal operation.
2. The overlay must pass pointer, wheel, touch where available, and keyboard
   interaction through. It must not grab focus, record input, capture the
   desktop, or draw over security screens. Never use a session-lock protocol.
3. Provide a project command `./bin/dimmer --stop` for normal recovery and
   `./bin/dimmer --kill` for immediate termination of the app's own service.
   The launcher must work independently of the Qt process. `--kill` must work
   even if that process is frozen.
4. Add an emergency KDE global shortcut that launches the independent recovery
   command. Prefer `Ctrl+Alt+Shift+D` if it is free. Respect existing assignments
   and document the actual binding. A shortcut handled only by the dimmer's
   event loop is not sufficient. Verify the KDE command-launching route during
   setup and test it with the dimmer process deliberately frozen.
5. Provide a separate application-menu emergency launcher as another way to run
   the same recovery command. Document the direct systemd recovery command too:
   `systemctl --user stop linux-custom-dimmer.service`.
6. Validate that this service belongs to this application before starting,
   stopping, or killing it. Reject an existing unit with a different executable
   or ownership record. Never use `killall`, broad `pkill`, command substring
   matching, or a stale PID file to identify a target. Do not signal KWin,
   Plasma, the user's shell, or any other application.
7. Keep any IPC local to the current user, with an owner-only runtime directory
   and a fixed set of accepted actions. No TCP port, arbitrary shell command,
   or arbitrary unit/PID parameter. Validate numeric input and reject NaN and
   malformed values as well as out-of-range values.
8. Confirm support and recovery before creating a visible overlay. If either is
   unavailable, remain Stopped and explain what is missing. Do not silently
   start a less recoverable implementation.
9. On exit, crash, termination, and compositor disconnection, release owned
   surfaces. Never automatically restart or reapply darkness after a failure,
   logout, login, suspend, or unlock.
10. Development previews must have an independent timed stop, outside the app's
    process group, in addition to their own timer. Test recovery using only
    disposable test processes and the dimmer itself. Never freeze or terminate
    other real applications for a test.

No program can promise that a graphics driver will never fail. The concrete
requirement is that this app changes only its own windows, has tightly scoped
process control, and provides recovery independent of its UI. The intentional
effect on other apps is visual dimming, with normal interaction preserved.

## Memory and battery expectations

Use no browser engine, Node runtime, continuous animation, framebuffer copying,
screen capture, busy loop, or permanently running helper daemon. Use event
notifications instead of repeated environment and display queries. Coalesce
slider events if needed and stop update timers as soon as interaction ends.

The quiet test at 65% opacity measured 7.13 W before, 7.22 W during, and 7.19 W
after dimming. The observed difference was about 0.06 W, or 0.9%, near ordinary
measurement variation. The preview used about 53.4 MiB proportional memory and
176.4 MiB resident memory including shared libraries, with no measurable CPU
time after startup. The compositor also used memory and did the blending.

Treat those as reference observations, not guarantees. Aim for near-zero idle
CPU and similar proportional memory; investigate idle CPU above 0.2% of one
core or application proportional memory above 100 MiB after warm-up. Report
actual measurements and causes rather than hiding a missed target. Measure
idle and video workloads because overlays can change compositor behavior.

Do not promise battery savings. Backlight power is unchanged. The first noisy
test suggested 11% extra power and was not reliable evidence of overlay cost.
A later 1000K Night Light run averaged 7.40 W, but the earlier tests did not
record Night Light state, so no clean efficiency winner was established.

## Development and Git workflow

Keep work inside this project. Use a local Git repository, meaningful milestone
commits, and focused staging. If a repository already exists, inspect its
instructions, history, status, and current branch first. Preserve unrelated
or uncommitted work. Do not initialize or stage a parent repository by accident.

Track source, build instructions, tests, dependency declarations, documentation,
and summarized verification evidence. Ignore `.venv`, caches, generated native
binaries, build output, profiler dumps, credentials, and raw local logs. Avoid
`git add .` when unrelated files could be present. Never force-push, reset
unrelated work, rewrite shared history, create a remote, or publish automatically.

Use commits such as `docs: record dimmer scope and evidence`,
`chore: prepare native development environment`,
`feat: add isolated launch and emergency recovery`,
`feat: add neutral overlay and controls`, and
`test: verify crash recovery and record resource usage`.
Run checks relevant to each commit. Record any unavailable checks honestly.
Initialize the package version in `pyproject.toml`; create a local `v0.1.0` tag
only after the release acceptance checks pass. No remote is required.

## The two prompts

### Prompt 1: prepare the base

Copy this in a Codex session opened in this folder:

```text
Read AGENTS.md, project-scope.md, docs/issues-and-decisions.md, docs/status.md,
docs/testing.md, and the implementation plan. Complete Stage 1 only: prepare the project's base,
Git repository, isolated development environment, compatible dependencies,
native adapter build, test tools, launch/recovery foundation, and documentation.
You have full architecture authority within the agreed scope. Resolve routine
implementation choices yourself and record the reasons. Prove the safety
foundation with harmless test processes and only short automatically expiring
display probes when needed. Record every significant issue and its fix, tests
run, dependency/install changes, and remaining work. Make meaningful local Git
commits. Leave the project ready for the next instruction, "build the app".
Do not build the complete product UI or leave any dimmer running in this stage.
```

### Prompt 2: finish the app

```text
build the app
```

The second prompt means execute Stage 2 from the committed handoff: implement
the product, validate emergency recovery and process isolation, run meaningful
tests, measure resources, supply local launch and uninstall instructions, update
the issue/decision records and status, and commit the finished work. Do not
restart the requirements discussion or add unrelated features. Normal tool
permissions still apply, and genuinely missing access must be reported rather
than bypassed. No implementation work is requested in the current docs-only step.

See [the implementation plan](docs/superpowers/plans/2026-09-27-linux-custom-dimmer.md)
for tasks and completion criteria, and [the evidence and issue log](docs/issues-and-decisions.md)
for details that future sessions must not have to rediscover.

The [test plan](docs/testing.md) defines the automated checks, real process
isolation tests, live desktop acceptance, and resource measurements required
before release. These are future implementation requirements, not tests passed
by this documentation handoff.
