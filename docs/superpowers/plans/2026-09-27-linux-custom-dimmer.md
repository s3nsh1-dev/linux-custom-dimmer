# Linux custom dimmer implementation plan

> For agentic workers: execute this plan task by task. Use the executing-plans
> skill when available. The user has delegated architecture decisions to Codex;
> the two prompts select the stages below. Read the spec and current status first.

**Goal:** Deliver a small recoverable Python app that controls a neutral dimming
overlay independently of the laptop's hardware brightness.

**Architecture:** One PyQt6 application contains a normal control window and an
input-transparent layer-shell overlay. A small native adapter configures the
overlay through public Qt/LayerShellQt interfaces. A dedicated transient
systemd user service and an external recovery launcher scope termination to
this app and allow recovery if its UI freezes.

**Tech stack:** Python 3, distro PyQt6/Qt6, LayerShellQt, a minimal C++ adapter
if needed, systemd user services, pytest, and Ruff. No web runtime.

**Spec:** [project-scope.md](../../../project-scope.md).

**Test plan:** [docs/testing.md](../../testing.md). Apply its cases to the
corresponding tasks below and record actual results in `docs/verification.md`.

## Global constraints

- Initial support is the current Ubuntu KDE Wayland laptop.
- The overlay adds neutral black; hardware brightness and Night Light stay unchanged.
- Launch Stopped; opacity range 0% through 80%; no automatic start or restart.
- An external emergency route must terminate only the verified dimmer service.
- No broad process killing, root runtime, screen capture, polling renderer, or network service.
- Preserve user work, keep artifacts local, and commit verified milestones.
- Codex may refine file boundaries and supported interop details without another design round; record reasons and preserve requirements.

## Review focus

1. An existing unrelated service has the same proposed unit name: refuse to use or kill it. Test in Task 2.
2. The dimmer freezes while the screen is dark: the external recovery path still works. Test in Tasks 2 and 6.
3. A window becomes modal or a popup takes focus: the overlay still passes input and the shortcut still exits. Test in Tasks 4 and 6.
4. A screen is removed, resized, scaled, locked, or suspended: remove the layer and return Stopped. Test in Task 5.
5. Duplicate launches or malformed opacity/IPC input: never stack overlays, execute arbitrary commands, or create full black. Test in Tasks 3 and 5.

## Proposed file ownership

| Files | Responsibility |
| --- | --- |
| `pyproject.toml`, `.gitignore`, `README.md`, `scripts/setup-dev`, `scripts/check` | Version, dependencies, reproducible setup, and checks. |
| `native/CMakeLists.txt`, `native/layer_shell_bridge.cpp` | Small public-API adapter, built into ignored `build/`. |
| `src/linux_custom_dimmer/__main__.py`, `app.py` | Application lifetime and integration. |
| `src/linux_custom_dimmer/state.py` | Validated opacity and explicit Active/Stopped transitions. |
| `src/linux_custom_dimmer/overlay.py`, `native.py` | Rendering, layer-shell setup, and native library boundary. |
| `src/linux_custom_dimmer/window.py` | Native slider, state label, and buttons. |
| `src/linux_custom_dimmer/session.py` | Screen/session changes and removal on unsafe transitions. |
| `src/linux_custom_dimmer/control.py`, `bin/dimmer` | Independent launch, show, stop, kill, and verified service identity. |
| `resources/`, `scripts/install-local`, `scripts/uninstall-local` | Main and emergency launchers, explicit reversible desktop integration. |
| `tests/test_state.py`, `tests/test_control.py`, `tests/test_overlay.py`, `tests/test_session.py` | Meaningful behavior and failure tests. |
| `tests/integration/`, `scripts/measure-resources` | Opt-in live recovery checks and resource comparisons. |
| `docs/issues-and-decisions.md`, `docs/status.md`, `docs/verification.md` | Troubleshooting history, handoff, and acceptance evidence. |

These are planned files. Do not treat the current documentation-only repository
as if they already exist. Avoid creating empty production modules merely to
match the table; create each when its task needs it.

## Stage 1: base setup prompt

### Task 1: establish the reproducible project

- [x] Inspect this folder and applicable instructions. Verify that Git operations
  target this project, not its parent. Preserve any existing user changes.
- [x] Initialize local Git only if absent. Add a focused ignore file for `.venv`,
  `build`, `dist`, bytecode, tool caches, raw profiling output, and local secrets.
  Make a first documentation commit using explicit paths.
- [x] Create `pyproject.toml` with package metadata, version `0.1.0.dev0`, pytest
  and Ruff configuration, and a documented distro-provided PyQt6 requirement.
- [x] Prepare a project virtual environment that can import the installed PyQt6.
  Keep developer-only tools there; do not install a competing Qt from pip.
- [x] Verify Python, PyQt6, Qt, LayerShellQt, compiler, build tool, Wayland, and
  user-service versions. Install only missing required dependencies through the
  appropriate package mechanism, honoring environment permissions. Record all
  installation locations and exact reproducible commands.
- [x] Implement an idempotent `scripts/setup-dev` and `scripts/check`. The latter
  runs the native build, Python import/compile checks, Ruff, and existing tests.
  It must not start a live overlay or change desktop settings.
- [x] Document the initial run/build/recovery contract in README and update status.
  Commit `chore: prepare native development environment` after these checks pass.

### Task 2: prove independent, scoped recovery

- [x] Establish `bin/dimmer` command semantics: no arguments launches/shows the
  app, `--stop` requests service shutdown, and `--kill` terminates only the
  verified dimmer unit. Keep this CLI independent of Qt imports and the GUI loop.
- [x] Define a fixed application identity and trusted expected executable path.
  Verify service identity before every destructive operation; reject collisions.
  Use argument arrays or D-Bus calls, never interpolated shell command strings.
- [x] In `tests/test_control.py`, write behavior tests first for unit collisions,
  missing units, duplicate launches, paths containing spaces, and rejection of
  unexpected arguments. Assert that no stop/kill call targets an unrelated unit.
- [x] Implement transient user-service launch and lifecycle properties from the
  spec. Do not enable a startup service or change other services.
- [x] Use a harmless dummy program to verify normal stop and forced termination.
  Freeze only this owned dummy with SIGSTOP; prove the external recovery command
  ends it within a documented timeout. Run an unrelated disposable sentinel and
  assert it survives. Verify that no test units or child processes remain.
- [x] Determine and document the supported KDE mechanism for binding a global
  shortcut to an external command. Check availability and collision handling.
  Do not substitute a callback that depends on the app's own event loop. Record
  installation/removal paths; final binding is part of Stage 2 integration.
- [x] Commit `feat: add isolated launch and emergency recovery` with test results.

### Task 3: prepare native integration and the build handoff

- [x] Build the narrow adapter against matching system Qt6 and LayerShellQt
  headers. Its only job is configuring a caller-owned live Qt window as the
  overlay. Export an unmangled interface, return explicit error status, and
  require main-thread calls and matching runtime libraries.
- [x] Keep adapter loading separate from rendering. Test missing library and
  unsupported-session paths without creating any visible window. They must
  leave the application Stopped.
- [x] If a live probe is needed to validate the adapter, use a short preview with
  a separate externally scheduled recovery deadline. No persistent settings,
  full-black surface, or long unattended experiment. Log the result and remove
  every preview process/timer afterward.
- [x] Create the initial pure state contract for Stage 2: `STOPPED`/`ACTIVE`,
  selected opacity 0..80, and idempotent stop. Do not build the complete UI yet.
  Pin invalid-input handling and zero-opacity behavior with a focused test.
- [x] Record unresolved failures accurately. Update the issue log and status
  with exact development commands, compatibility findings, local installation
  changes, Git commits, and the next task. The handoff must require no previous
  chat history or files in `/tmp`.
- [x] Commit the native foundation and handoff. Run `scripts/check`, inspect
  Git status, and verify no dimmer process is running. Stage 1 is ready only
  when the build and dummy recovery work; do not hide a blocked prerequisite.

## Stage 2: user says `build the app`

Implementation checkpoint: `405708d` (2026-09-28). Required hands-on
acceptance remains open at the owner's request; this stage is not release-complete.
See `docs/verification.md` for the exact split between automated evidence and
pending physical key/input/session checks.

### Task 4: implement the neutral overlay and native controls

- [x] Read the committed Stage 1 status and verify its commands still work.
  Use the current clean task branch or a focused local feature branch. Do not
  discard existing work or repeat setup that is already verified.
- [x] Implement `overlay.py` using the verified adapter and Qt raster drawing.
  Use one alpha-enabled surface for the built-in display, input transparency,
  no focus or keyboard interactivity, and no exclusive space reservation.
- [x] Write focused tests around surface creation/removal, opacity limits,
  unchanged-value updates, and error cleanup. An inactive or unchanged overlay
  must not schedule repeated paints. A failed surface must be destroyed.
- [x] Implement `window.py` with a labelled native slider, Start, Stop, and the
  emergency button. Connect it through the state/controller boundary; do not
  let widget construction create a dark layer. Supply normal keyboard access.
- [x] Validate the state table from the scope: launch Stopped, Start at 50%,
  active slider changes, 0% stops, stopped slider changes do not start, repeated
  Stop is harmless, and window close removes the layer.
- [ ] Test interaction with a separate disposable window, popups, scrolling,
  typing, and fullscreen content. Capture actual findings; mocks alone cannot
  establish click-through or correct compositor stacking.
- [x] Commit `feat: add neutral overlay and controls` after relevant checks.

### Task 5: lifecycle, single instance, and local integration

- [x] Connect screen geometry/removal and session lock/suspend notifications.
  On these events, remove the layer and remain Stopped until Start is requested.
  Do not place the overlay above lock/security surfaces or take exclusive input.
- [ ] Test event handling with injected notifications, and perform live checks
  where practical. Display changes must not leave an orphan or duplicated layer.
- [x] Implement single-instance/show behavior with owner-only local IPC if
  needed. Validate fixed actions and opacity values; reject malformed payloads.
  A second launch must not create another overlay or kill the first app.
- [x] Add local launch/install/uninstall scripts. Record every external path
  created, including main/emergency launchers and shortcut registration. Use the
  existing user-service manager; do not create root services or autostart entries.
- [x] Register the actual available emergency shortcut to the independent
  recovery command. Preserve existing shortcuts. If a required desktop step
  needs user interaction or permission, explain the concrete need; do not mark
  the shortcut working before it has been exercised.
- [x] Verify Start stays disabled if independent recovery is unavailable.
  Commit the lifecycle and integration changes with the tests run.

### Task 6: failure recovery, resources, and final handoff

- [ ] Test normal Stop, window close, quit, SIGTERM, and forced termination.
  Verify owned surfaces disappear and no hardware/color setting changes.
- [ ] With an external timed fallback armed, freeze only the dimmer process.
  Verify the independent emergency launcher and global shortcut terminate its
  service even when its event loop cannot run. The unrelated test sentinel must
  remain alive. Never target unrelated real applications or the compositor.
- [x] Repeat launch/stop cycles, exercise the maximum permitted opacity, and
  test invalid inputs and service-name collisions. Verify no lingering timers,
  child processes, or duplicate overlays remain after cleanup.
- [x] Measure a warmed-up final app, not just the prototype. Record application
  CPU/RSS/PSS, compositor/GPU activity, backlight, battery status, Night Light
  state, and an idle OFF/ON/OFF comparison. Preserve raw logs locally and commit
  concise summaries. Include a video workload when available; label omitted
  or inconclusive results. Do not infer battery-life savings from a short run.
- [x] Run all relevant automated checks and inspect the final diff for unrelated
  changes, unsafe process targeting, dependency/runtime mismatches, and logging
  or rendering loops. Record the actual live acceptance results in
  `docs/verification.md`.
- [x] Update README with exact launch, Start/Stop, emergency recovery,
  compatibility, limitations, and uninstall instructions. Complete the issue
  log and status with final commits and all integration locations.
- [ ] Commit verified milestones, set version `0.1.0`, and add a local `v0.1.0`
  tag only if required acceptance checks passed. Do not push or publish.
  Finish with the screen undimmed and the app Stopped or closed, and report how
  the user can launch it and immediately stop it.

## Completion standard

The product is complete when the accepted neutral effect is controllable,
normal input still works, settings are untouched, recovery survives a frozen
app, unrelated processes survive all recovery tests, and installation/removal
and resource use are documented. An attractive window without verified escape
routes is not complete. Passing unit tests alone is not proof of live Wayland
behavior. Report any real blocker specifically instead of claiming completion.
