import pytest

from linux_custom_dimmer.state import Mode, State


@pytest.mark.parametrize("opacity", [0, 1, 50, 65, 80])
def test_select_does_not_start_and_zero_removes_active_layer(opacity):
    state = State()
    assert state.opacity == 50 and state.mode is Mode.STOPPED
    state.select(opacity)
    assert state.effective_opacity == 0
    state.start()
    assert state.effective_opacity == opacity
    state.select(0)
    assert state.mode is Mode.STOPPED
    state.select(65)
    assert state.effective_opacity == 0
    state.start()
    assert state.effective_opacity == 65
    state.stop()
    state.stop()
    assert state.mode is Mode.STOPPED


@pytest.mark.parametrize(
    "value", [-1, 81, 255, "50", "nan", None, True, 50.0, float("nan"), float("inf"), -float("inf")]
)
def test_invalid_opacity_never_changes_selected_or_active_value(value):
    state = State()
    state.start()
    with pytest.raises(ValueError):
        state.select(value)
    assert state.opacity == 50 and state.effective_opacity == 50
