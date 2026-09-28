from pathlib import Path
from types import SimpleNamespace

import pytest

from linux_custom_dimmer.integration import KEY, Integration, KDEShortcuts


class Shortcuts:
    def __init__(self, available=True):
        self.free = available
        self.bound = False
        self.keys = [KEY]

    def available(self):
        return self.free

    def registered(self):
        return self.bound and self.keys == [KEY]

    def snapshot(self):
        return (list(self.keys), True) if self.bound else None

    def restore(self, snapshot):
        self.bound = snapshot is not None
        if snapshot:
            self.keys = list(snapshot[0])

    def register(self):
        self.bound = True
        self.keys = [KEY]

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
    # KDE considers a key held by this same action unavailable too.
    backend.free = False
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


@pytest.mark.parametrize("operation", ["install", "uninstall"])
def test_existing_registration_without_owned_entry_is_preserved(tmp_path, operation):
    backend = Shortcuts()
    backend.bound = True
    backend.keys = [123]
    integration = Integration(Path("/project"), tmp_path, backend, lambda: None)
    before = backend.snapshot()
    with pytest.raises(RuntimeError, match="ownership"):
        getattr(integration, operation)()
    assert backend.snapshot() == before
    assert all(not path.exists() for path in integration.entries())


def test_failed_repair_restores_preexisting_owned_registration(tmp_path):
    class BrokenRepair(Shortcuts):
        broken = False

        def register(self):
            super().register()
            if self.broken:
                raise RuntimeError("failed after changing keys")

    backend = BrokenRepair()
    integration = Integration(Path("/project"), tmp_path, backend, lambda: None)
    integration.install()
    backend.keys = [123]
    backend.broken = True
    before = backend.snapshot()
    with pytest.raises(RuntimeError, match="failed after"):
        integration.install()
    assert backend.snapshot() == before
    assert all(path.exists() for path in integration.entries())


def test_cache_failure_after_registration_also_rolls_back(tmp_path):
    backend = Shortcuts()
    calls = []

    def refresh():
        calls.append(True)
        if len(calls) == 1:
            backend.bound = True  # KDE may discover the new desktop during refresh.
            raise RuntimeError("cache refresh failed")

    integration = Integration(Path("/project"), tmp_path, backend, refresh)
    with pytest.raises(RuntimeError, match="cache refresh"):
        integration.install()
    assert not backend.bound
    assert all(not path.exists() for path in integration.entries())


@pytest.mark.parametrize("names,expected", [([], None), (["_launch"], ([], False))])
def test_empty_kde_component_is_distinct_from_unbound_action(monkeypatch, names, expected):
    backend = KDEShortcuts.__new__(KDEShortcuts)
    backend.manager = SimpleNamespace(
        getComponent=lambda *a, **kw: "/component", shortcut=lambda *a, **kw: []
    )
    backend.bus = SimpleNamespace(get_object=lambda *a: object())
    component = SimpleNamespace(shortcutNames=lambda **kw: names, isActive=lambda **kw: False)
    monkeypatch.setattr("linux_custom_dimmer.integration.dbus.Interface", lambda *a: component)
    assert backend.snapshot() == expected
