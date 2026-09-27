"""Failure injection for test-resource cleanup, with no live desktop calls."""

from contextlib import ExitStack

import pytest

from tests.integration.resources import temporary_desktop


@pytest.mark.parametrize("failure", ["connect", "body", "unregister"])
def test_desktop_is_removed_and_cache_refreshed_even_when_setup_or_cleanup_fails(tmp_path, failure):
    desktop = tmp_path / "probe.desktop"
    events = []

    class Manager:
        def unregister(self, component, action):
            events.append("unregister")
            if failure == "unregister":
                raise RuntimeError("unregister failed")

    def connect():
        if failure == "connect":
            raise RuntimeError("connect failed")
        return Manager()

    def refresh():
        assert not desktop.exists()
        events.append("refresh")

    with pytest.raises(RuntimeError, match=failure):
        with temporary_desktop(desktop, "test command", connect, refresh):
            assert desktop.read_text() == "test command"
            if failure == "body":
                raise RuntimeError("body failed")
    assert not desktop.exists()
    assert events[-1] == "refresh"


def test_existing_desktop_is_never_removed(tmp_path):
    desktop = tmp_path / "probe.desktop"
    desktop.write_text("unrelated entry")
    with pytest.raises(FileExistsError):
        with temporary_desktop(desktop, "replacement", lambda: None, lambda: None):
            pytest.fail("must refuse collision")
    assert desktop.read_text() == "unrelated entry"


def test_recovery_error_still_releases_all_outer_resources(tmp_path):
    desktop = tmp_path / "probe.desktop"
    events = []

    class Manager:
        def unregister(self, *args):
            events.append("unregistered")

    def kill():
        raise RuntimeError("recovery unavailable")

    with pytest.raises(RuntimeError, match="recovery unavailable"):
        with temporary_desktop(desktop, "probe", Manager, lambda: events.append("refreshed")):
            with ExitStack() as resources:
                resources.callback(lambda: events.append("sentinel stopped"))
                resources.callback(kill)
    assert events == ["sentinel stopped", "unregistered", "refreshed"]
    assert not desktop.exists()
