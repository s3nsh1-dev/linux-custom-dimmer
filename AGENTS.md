# Project instructions

This project is a small Python neutral screen dimmer for the owner's Ubuntu
KDE Wayland laptop. Read these files before working:

- `project-scope.md`: agreed requirements, safety rules, stack, and two prompts.
- `docs/superpowers/plans/2026-09-27-linux-custom-dimmer.md`: staged work plan.
- `docs/issues-and-decisions.md`: prior experiments, problems, and decisions.
- `docs/status.md`: completed work, current stage, checks, and next actions.
- `docs/testing.md`: automated and live acceptance tests and performance method.

The user explicitly gives Codex architecture authority within this scope.
Make routine implementation decisions autonomously and document them. Do not
restart design questionnaires or require separate approval for each architecture
choice. Honor tool permissions and ask only for genuinely missing information,
required privileges, or a material scope change.

The base-setup prompt authorizes Stage 1. A later instruction saying
`build the app` authorizes Stage 2 end to end, including implementation,
validation, local launch integration, documentation, and local Git commits.
Do not claim a stage complete when its required checks are unverified.

Use Python, PyQt6, and the tested neutral overlay approach. Keep it native and
small. Never substitute a hardware-brightness wrapper, tint adjustment,
Electron app, screenshot loop, or browser overlay. See the brief for the narrow
native adapter and independent emergency recovery design.

Protect unrelated processes and user work. Recovery may target only this
application's verified service/process group. Never use broad process-name
killing, restart the compositor, or change desktop power/color settings. A
frozen dimmer must be recoverable without its own UI responding. All temporary
probes must expire automatically, including if their own event loop freezes.

Use local Git version control with specific staging and meaningful commits
after relevant checks. Preserve existing changes. Do not push, publish, or
rewrite history unless separately instructed. Keep build output, virtual
environments, and local profiling data out of Git.

Update `docs/issues-and-decisions.md` when a significant issue occurs: symptom,
cause or uncertainty, fix, verification, and relevant commit. Update
`docs/status.md` at every stage boundary and before handing work back. Include
commands, test results, installed dependencies/integration, limitations, and the
next executable step. Distinguish observed results from assumptions.

Install plugins at project scope by default. Install at user scope only when
explicitly requested. If project scope is unsupported, explain before installing
elsewhere. No Codex plugin is currently required for this app.
