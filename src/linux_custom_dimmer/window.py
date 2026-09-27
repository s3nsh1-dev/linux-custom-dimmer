"""Compact native widgets; window construction never activates dimming."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget


class ControlWindow(QWidget):
    def __init__(self, controller, quit_app):
        super().__init__()
        self.controller = controller
        self.quit_app = quit_app
        self.setWindowTitle("Linux Custom Dimmer")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        self.status_label = QLabel("Stopped")
        font = self.status_label.font()
        font.setBold(True)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)
        row = QHBoxLayout()
        label = QLabel("&Extra dimming")
        self.value_label = QLabel("50%")
        row.addWidget(label)
        row.addStretch()
        row.addWidget(self.value_label)
        layout.addLayout(row)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 80)
        self.slider.setValue(50)
        self.slider.setPageStep(5)
        self.slider.setAccessibleName("Extra dimming")
        label.setBuddy(self.slider)
        layout.addWidget(self.slider)
        hint = QLabel("Higher means darker. 0% removes extra dimming.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        actions = QHBoxLayout()
        self.start_button = QPushButton("&Start")
        self.stop_button = QPushButton("S&top")
        actions.addWidget(self.start_button)
        actions.addWidget(self.stop_button)
        layout.addLayout(actions)
        self.emergency_button = QPushButton("&Emergency stop and quit")
        self.emergency_button.setMinimumHeight(40)
        font = self.emergency_button.font()
        font.setBold(True)
        self.emergency_button.setFont(font)
        layout.addWidget(self.emergency_button)
        self.recovery_hint = QLabel("Emergency shortcut: Ctrl+Alt+Shift+D")
        self.recovery_hint.setWordWrap(True)
        layout.addWidget(self.recovery_hint)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.message)
        self.slider.valueChanged.connect(controller.select)
        self.start_button.clicked.connect(controller.start)
        self.stop_button.clicked.connect(lambda: controller.stop())
        self.emergency_button.clicked.connect(self.emergency)
        controller.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        ctl = self.controller
        self.slider.blockSignals(True)
        self.slider.setValue(ctl.state.opacity)
        self.slider.blockSignals(False)
        self.value_label.setText(f"{ctl.state.opacity}%")
        self.status_label.setText(ctl.state.mode.value)
        self.start_button.setEnabled(
            ctl.available and ctl.overlay is None and ctl.state.opacity > 0
        )
        self.stop_button.setEnabled(ctl.overlay is not None)
        self.message.setText(ctl.message)
        self.message.setVisible(bool(ctl.message))

    def emergency(self):
        self.controller.stop()
        self.quit_app()

    def closeEvent(self, event):
        self.controller.stop()
        event.accept()
        self.quit_app()

    def show_existing(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.controller.check_ready()
