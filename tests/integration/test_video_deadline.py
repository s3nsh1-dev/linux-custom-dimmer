"""Only a disposable generated video window; verify its independent deadline."""

import os
import runpy
import signal
import subprocess
import time
from pathlib import Path

import pytest

from tests.integration.test_app import absent, owned_signal
from tests.integration.test_recovery import ROOT, process_identity, wait_for

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("DIMMER_VIDEO_TESTS") != "1", reason="explicit live opt-in"),
]


def test_frozen_video_expires_without_sampler_cleanup():
    helpers = runpy.run_path(str(ROOT / "scripts/measure-resources"))
    ctl = helpers["video_controller"](ROOT, Path(os.environ["XDG_RUNTIME_DIR"]), 10)
    video = ROOT / ".local/measurement-video.mp4"
    video.parent.mkdir(exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=gray:s=160x90:r=10",
            "-t",
            "1",
            "-c:v",
            "mpeg4",
            str(video),
        ],
        check=True,
        timeout=10,
    )
    try:
        ctl.perform("launch", runtime_limit=1)

        def running():
            with ctl.backend.pinned(ctl.identity.unit) as props:
                return props is not None and props["MainPID"]

        wait_for(running)
        pid = owned_signal(ctl, signal.SIGSTOP)
        wait_for(lambda: process_identity(pid)[0] == "T")
        started = time.monotonic()
        wait_for(lambda: absent(ctl), timeout=5)
        assert process_identity(pid) is None
        print(f"Frozen video independently expired in {time.monotonic() - started:.3f}s")
    finally:
        ctl.perform("kill")
