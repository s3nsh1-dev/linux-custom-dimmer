"""Fixed disposable-test recovery command, launched externally by KDE."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from linux_custom_dimmer.control import Controller, Identity  # noqa: E402
from linux_custom_dimmer.service import Systemd  # noqa: E402


class DummyIdentity(Identity):
    @property
    def argv(self):
        return ["/usr/bin/python3", "-I", str(ROOT / "tests/integration/dummy.py"), "--freeze"]


if __name__ == "__main__":
    print(
        Controller(
            DummyIdentity(ROOT, "linux-custom-dimmer-kde-probe.service"),
            Path(os.environ["XDG_RUNTIME_DIR"]),
            Systemd(),
        ).perform("kill")
    )
