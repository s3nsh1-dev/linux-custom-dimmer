"""Bounded preflight only. No window creation or repeated desktop polling."""

import os
import re
import subprocess


class SupportError(RuntimeError):
    pass


def check_session(environment=None, run=subprocess.run):
    env = os.environ if environment is None else environment
    if (
        env.get("XDG_SESSION_TYPE") != "wayland"
        or "KDE" not in env.get("XDG_CURRENT_DESKTOP", "").split(":")
        or not env.get("WAYLAND_DISPLAY")
    ):
        raise SupportError("This version requires a KDE Wayland session")
    if env.get("QT_WAYLAND_SHELL_INTEGRATION"):
        raise SupportError("Remove the global QT_WAYLAND_SHELL_INTEGRATION override")
    try:
        result = run(
            ["/usr/bin/wayland-info"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise SupportError(
            "Could not verify Wayland layer-shell support with wayland-info"
        ) from error
    if not re.search(r"interface:\s*'zwlr_layer_shell_v1',\s*version:\s*[1-9]", result.stdout):
        raise SupportError("Compositor does not advertise the layer-shell protocol")
