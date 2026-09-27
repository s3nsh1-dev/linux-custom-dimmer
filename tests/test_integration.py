from pathlib import Path

import pytest

from linux_custom_dimmer.integration import Integration


class Shortcuts:
    def __init__(self, available=True):
        self.free = available
        self.bound = False

    def available(self):
        return self.free

    def registered(self):
        return self.bound

    def register(self):
        self.bound = True

    def unregister(self):
        self.bound = False


def test_install_and_remove_only_owned_launchers(tmp_path):
    backend = Shortcuts()
    integration = Integration(Path("/project with spaces"), tmp_path, backend, lambda: None)
    integration.install()
    integration.verify()
    unrelated = tmp_path / "applications/other.desktop"
    unrelated.write_text("not ours")
    before = {path: path.read_text() for path in integration.entries()}
    integration.install()
    assert before == {path: path.read_text() for path in integration.entries()}
    assert '"/project with spaces/bin/dimmer" --kill' in next(
        text for text in before.values() if "--kill" in text
    )
    integration.uninstall()
    assert not backend.bound and unrelated.read_text() == "not ours"
    assert all(not path.exists() for path in integration.entries())


def test_shortcut_collision_prevents_writing_files(tmp_path):
    integration = Integration(Path("/project"), tmp_path, Shortcuts(False), lambda: None)
    with pytest.raises(RuntimeError, match="already assigned"):
        integration.install()
    assert all(not path.exists() for path in integration.entries())


def test_foreign_desktop_entry_is_never_overwritten_or_removed(tmp_path):
    integration = Integration(Path("/project"), tmp_path, Shortcuts(), lambda: None)
    path = next(iter(integration.entries()))
    path.parent.mkdir(parents=True)
    path.write_text("unrelated")
    for operation in (integration.install, integration.uninstall):
        with pytest.raises(RuntimeError, match="Refusing"):
            operation()
    assert path.read_text() == "unrelated"


def test_failed_registration_rolls_back_our_new_files(tmp_path):
    class Broken(Shortcuts):
        def register(self):
            raise RuntimeError("cannot register")

    backend = Broken()
    integration = Integration(Path("/project"), tmp_path, backend, lambda: None)
    with pytest.raises(RuntimeError):
        integration.install()
    assert all(not path.exists() for path in integration.entries())
