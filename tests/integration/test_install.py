"""Explicit reversible check of this checkout's actual user integration."""

import hashlib
import os
import subprocess

import pytest

from linux_custom_dimmer.control import Identity
from linux_custom_dimmer.integration import COMPONENT, Integration
from tests.integration.test_app import absent
from tests.integration.test_recovery import ROOT, controller, wait_for

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("DIMMER_INSTALL_TESTS") != "1", reason="explicit live opt-in"
    ),
]


def test_install_remove_reinstall_preserves_other_entries_and_shortcuts():
    integration = Integration(ROOT)
    integration.verify()
    manager = integration.shortcuts.manager

    def unrelated():
        keys = {}
        for main in manager.allMainComponents(timeout=2):
            if str(main[0]) != COMPONENT:
                for action in manager.allActionsForComponent(main, timeout=2):
                    keys[tuple(str(item) for item in action)] = list(
                        manager.shortcut(action, timeout=2)
                    )
        owned = set(integration.entries())
        files = {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (integration.data_home / "applications").rglob("*.desktop")
            if path not in owned and path.is_file()
        }
        return keys, files

    before = unrelated()
    ctl = controller(Identity(ROOT))
    with ctl.backend.pinned(ctl.identity.unit) as props:
        assert props is None, "Close the existing dimmer before install testing"
    ctl.perform("launch", runtime_limit=10)
    try:
        subprocess.run([ROOT / "scripts/uninstall-local"], check=True, timeout=15)
        wait_for(lambda: absent(ctl))
        assert integration.shortcuts.snapshot() is None
        assert all(not path.exists() for path in integration.entries())
        assert unrelated() == before
        # Repeated removal must also be harmless.
        subprocess.run([ROOT / "scripts/uninstall-local"], check=True, timeout=15)
    finally:
        try:
            ctl.perform("kill")
        finally:
            subprocess.run([ROOT / "scripts/install-local"], check=True, timeout=15)
    subprocess.run([ROOT / "scripts/install-local"], check=True, timeout=15)
    integration.verify()
    assert unrelated() == before
    for path in integration.entries():
        subprocess.run(["desktop-file-validate", path], check=True, timeout=5)
    print(f"Preserved {len(before[0])} unrelated shortcut actions and {len(before[1])} entries")
