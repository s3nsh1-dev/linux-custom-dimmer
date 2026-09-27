import pytest
from PyQt6 import sip
from PyQt6.QtTest import QTest

from linux_custom_dimmer.overlay import RasterOverlay


class OffscreenBridge:
    def configure(self, window):
        pass


def test_real_raster_draws_only_after_show_and_on_changes(qt_app):
    overlay = RasterOverlay(qt_app.primaryScreen(), 50, OffscreenBridge())
    assert overlay.paint_count == 0 and not overlay.isVisible()
    overlay.show()
    QTest.qWait(80)
    assert overlay.paint_count >= 1
    count = overlay.paint_count
    overlay.set_opacity(50)
    QTest.qWait(80)
    assert overlay.paint_count == count
    overlay.set_opacity(65)
    QTest.qWait(80)
    assert overlay.paint_count == count + 1
    overlay.dispose()
    QTest.qWait(10)
    assert sip.isdeleted(overlay)


@pytest.mark.parametrize("value", [-1, 0, 81, 255, True, "50", float("nan"), float("inf")])
def test_overlay_never_accepts_unsafe_opacity(qt_app, value):
    with pytest.raises(ValueError):
        RasterOverlay(qt_app.primaryScreen(), value, OffscreenBridge())


def test_failed_native_configuration_destroys_window(qt_app):
    windows = []

    class BrokenBridge:
        def configure(self, window):
            windows.append(window)
            raise RuntimeError("native failure")

    with pytest.raises(RuntimeError, match="native failure"):
        RasterOverlay(qt_app.primaryScreen(), 50, BrokenBridge())
    assert sip.isdeleted(windows[0])
