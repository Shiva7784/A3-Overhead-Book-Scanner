"""Left sidebar for camera device selection and direct UVC hardware controls."""
from typing import Dict
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QGroupBox,
    QSlider,
    QCheckBox,
    QLineEdit,
    QScrollArea,
)
from PySide6.QtCore import Qt

from camera import UvcControl


class CameraPanel(QWidget):
    """Camera settings, UVC controls, and source management."""

    connect_requested = Signal(str, int, int, int, str)  # mode, dev_idx, target_w, target_h, stream_url
    disconnect_requested = Signal()
    control_changed = Signal(str, float)  # control_name, value
    reset_controls_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.setMaximumWidth(340)

        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(12)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 1. Device Selection Group
        dev_group = QGroupBox("Camera Source")
        dev_layout = QVBoxLayout(dev_group)
        dev_layout.setSpacing(8)

        # Mode Selector
        dev_layout.addWidget(QLabel("Source Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Physical UVC 4K Camera",
            "Mock Image Folder",
            "IP / Phone Stream (HTTP/RTSP)",
        ])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        dev_layout.addWidget(self.mode_combo)

        # Device Selection (for physical camera)
        self.device_label = QLabel("Device:")
        dev_layout.addWidget(self.device_label)

        self.device_row_widget = QWidget()
        dev_row_layout = QHBoxLayout(self.device_row_widget)
        dev_row_layout.setContentsMargins(0, 0, 0, 0)
        dev_row_layout.setSpacing(6)

        self.device_combo = QComboBox()
        dev_row_layout.addWidget(self.device_combo, stretch=1)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setToolTip("Scan and refresh connected cameras")
        self.btn_refresh.clicked.connect(self.refresh_devices)
        dev_row_layout.addWidget(self.btn_refresh)

        dev_layout.addWidget(self.device_row_widget)

        # Stream URL Input (for IP / Phone Stream mode)
        self.ip_label = QLabel("Phone Stream URL (HTTP/RTSP):")
        dev_layout.addWidget(self.ip_label)
        self.ip_input = QLineEdit("http://192.168.42.129:8080/video")
        self.ip_input.setPlaceholderText("http://<phone-ip>:8080/video")
        dev_layout.addWidget(self.ip_input)
        self.ip_label.setVisible(False)
        self.ip_input.setVisible(False)

        # Target Resolution
        dev_layout.addWidget(QLabel("Target Resolution:"))
        self.res_combo = QComboBox()
        self.res_combo.addItems([
            "3840 x 2160 (4K UHD)",
            "1920 x 1080 (Full HD)",
            "1280 x 720 (HD)",
        ])
        dev_layout.addWidget(self.res_combo)

        # Status & Connect Button
        btn_layout = QHBoxLayout()
        self.status_indicator = QLabel("● Disconnected")
        self.status_indicator.setStyleSheet("color: #ef4444; font-weight: bold;")
        btn_layout.addWidget(self.status_indicator)

        self.btn_toggle_connect = QPushButton("Connect")
        self.btn_toggle_connect.clicked.connect(self._toggle_connection)
        btn_layout.addWidget(self.btn_toggle_connect)
        dev_layout.addLayout(btn_layout)

        layout.addWidget(dev_group)

        # 2. Hardware UVC Controls Group
        self.uvc_group = QGroupBox("UVC Hardware Controls")
        uvc_layout = QVBoxLayout(self.uvc_group)
        uvc_layout.setSpacing(10)

        # Focus Control
        uvc_layout.addWidget(QLabel("Manual Focus:"))
        self.slider_focus = QSlider(Qt.Orientation.Horizontal)
        self.slider_focus.setRange(0, 255)
        self.slider_focus.setValue(50)
        self.slider_focus.valueChanged.connect(lambda v: self.control_changed.emit("focus", float(v)))
        uvc_layout.addWidget(self.slider_focus)

        self.chk_autofocus = QCheckBox("Autofocus")
        self.chk_autofocus.setChecked(False)
        self.chk_autofocus.toggled.connect(lambda c: self.control_changed.emit("autofocus", 1.0 if c else 0.0))
        uvc_layout.addWidget(self.chk_autofocus)

        # Exposure Control
        uvc_layout.addWidget(QLabel("Exposure Time:"))
        self.slider_exposure = QSlider(Qt.Orientation.Horizontal)
        self.slider_exposure.setRange(-13, 0)
        self.slider_exposure.setValue(-6)
        self.slider_exposure.setEnabled(False)  # Auto exposure is enabled by default
        self.slider_exposure.valueChanged.connect(lambda v: self.control_changed.emit("exposure", float(v)))
        uvc_layout.addWidget(self.slider_exposure)

        self.chk_auto_exposure = QCheckBox("Auto Exposure")
        self.chk_auto_exposure.setChecked(True)
        self.chk_auto_exposure.toggled.connect(self._on_auto_exposure_toggled)
        uvc_layout.addWidget(self.chk_auto_exposure)

        # Brightness & Contrast
        uvc_layout.addWidget(QLabel("Brightness:"))
        self.slider_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_brightness.setRange(-64, 64)
        self.slider_brightness.setValue(0)
        self.slider_brightness.valueChanged.connect(lambda v: self.control_changed.emit("brightness", float(v)))
        uvc_layout.addWidget(self.slider_brightness)

        uvc_layout.addWidget(QLabel("Contrast:"))
        self.slider_contrast = QSlider(Qt.Orientation.Horizontal)
        self.slider_contrast.setRange(0, 100)
        self.slider_contrast.setValue(50)
        self.slider_contrast.valueChanged.connect(lambda v: self.control_changed.emit("contrast", float(v)))
        uvc_layout.addWidget(self.slider_contrast)

        uvc_layout.addWidget(QLabel("Color Saturation:"))
        self.slider_saturation = QSlider(Qt.Orientation.Horizontal)
        self.slider_saturation.setRange(0, 128)
        self.slider_saturation.setValue(64)
        self.slider_saturation.valueChanged.connect(lambda v: self.control_changed.emit("saturation", float(v)))
        uvc_layout.addWidget(self.slider_saturation)

        self.btn_reset_uvc = QPushButton("↺ Reset Controls to Defaults")
        self.btn_reset_uvc.setToolTip("Restore calibrated camera exposure, brightness, and contrast")
        self.btn_reset_uvc.clicked.connect(self.reset_controls_requested.emit)
        uvc_layout.addWidget(self.btn_reset_uvc)

        layout.addWidget(self.uvc_group)

        # 3. Hardware Diagnostics Box
        diag_group = QGroupBox("Hardware Info")
        diag_layout = QVBoxLayout(diag_group)
        self.lbl_hw_info = QLabel("Driver: Uninitialized\nNegotiated: None\nFramerate: 0.0 fps")
        self.lbl_hw_info.setStyleSheet("color: #94a3b8; font-size: 11px;")
        diag_layout.addWidget(self.lbl_hw_info)
        layout.addWidget(diag_group)

        layout.addStretch()

        scroll_area.setWidget(container)
        outer_layout.addWidget(scroll_area)

        self._is_connected = False
        self.refresh_devices()

    def refresh_devices(self) -> None:
        """Enumerate connected physical video devices and populate the device combo box."""
        current_data = self.device_combo.currentData()
        self.device_combo.clear()

        devices = []
        try:
            from pygrabber.dshow_graph import FilterGraph
            graph = FilterGraph()
            names = graph.get_input_devices()
            for idx, name in enumerate(names):
                devices.append((idx, name))
        except Exception:
            pass

        if not devices:
            import cv2
            for idx in range(4):
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    devices.append((idx, f"Camera {idx}"))
                    cap.release()

        if devices:
            target_idx = 0
            for i, (idx, name) in enumerate(devices):
                self.device_combo.addItem(f"[{idx}] {name}", idx)
                if current_data is not None and idx == current_data:
                    target_idx = i
            self.device_combo.setCurrentIndex(target_idx)
        else:
            self.device_combo.addItem("No Cameras Found", -1)

    def _on_mode_changed(self, index: int) -> None:
        is_physical = (index == 0)
        is_ip = (index == 2)

        self.device_row_widget.setVisible(is_physical)
        self.device_label.setVisible(is_physical)
        self.ip_label.setVisible(is_ip)
        self.ip_input.setVisible(is_ip)
        self.res_combo.setEnabled(is_physical)
        self.uvc_group.setVisible(is_physical)

    def get_selected_resolution(self) -> tuple:
        """Get (width, height) tuple from selected resolution text."""
        txt = self.res_combo.currentText()
        if "3840" in txt:
            return 3840, 2160
        elif "1920" in txt:
            return 1920, 1080
        elif "1280" in txt:
            return 1280, 720
        return 1920, 1080

    def _toggle_connection(self) -> None:
        if not self._is_connected:
            idx = self.mode_combo.currentIndex()
            if idx == 1:
                mode = "mock"
            elif idx == 2:
                mode = "ip"
            else:
                mode = "physical"

            dev_idx = self.device_combo.currentData()
            if dev_idx is None or dev_idx < 0:
                dev_idx = self.device_combo.currentIndex()
                if dev_idx < 0:
                    dev_idx = 0

            target_w, target_h = self.get_selected_resolution()
            stream_url = self.ip_input.text()
            self.connect_requested.emit(mode, dev_idx, target_w, target_h, stream_url)
        else:
            self.disconnect_requested.emit()

    def set_connected_state(self, connected: bool, details: str = "") -> None:
        self._is_connected = connected
        if connected:
            self.status_indicator.setText("● Connected")
            self.status_indicator.setStyleSheet("color: #10b981; font-weight: bold;")
            self.btn_toggle_connect.setText("Disconnect")
            self.mode_combo.setEnabled(False)
            self.device_combo.setEnabled(False)
            self.btn_refresh.setEnabled(False)
            self.res_combo.setEnabled(False)
            if details:
                self.lbl_hw_info.setText(details)
        else:
            self.status_indicator.setText("● Disconnected")
            self.status_indicator.setStyleSheet("color: #ef4444; font-weight: bold;")
            self.btn_toggle_connect.setText("Connect")
            self.mode_combo.setEnabled(True)
            self.btn_refresh.setEnabled(True)
            self.res_combo.setEnabled(True)
            self._on_mode_changed(self.mode_combo.currentIndex())
            self.lbl_hw_info.setText("Driver: Disconnected\nNegotiated: None\nFramerate: 0.0 fps")

    def _on_auto_exposure_toggled(self, checked: bool) -> None:
        self.slider_exposure.setEnabled(not checked)
        self.control_changed.emit("auto_exposure", 1.0 if checked else 0.0)

    def apply_control_values(self, values: Dict[str, float]) -> None:
        """Update slider positions to match hardware values without firing duplicate signals."""
        self.slider_brightness.blockSignals(True)
        self.slider_contrast.blockSignals(True)
        self.slider_saturation.blockSignals(True)
        self.slider_exposure.blockSignals(True)
        self.chk_auto_exposure.blockSignals(True)

        if "brightness" in values:
            self.slider_brightness.setValue(int(values["brightness"]))
        if "contrast" in values:
            self.slider_contrast.setValue(int(values["contrast"]))
        if "saturation" in values:
            self.slider_saturation.setValue(int(values["saturation"]))
        if "exposure" in values:
            self.slider_exposure.setValue(int(values["exposure"]))
        if "auto_exposure" in values:
            auto_on = values["auto_exposure"] > 0.5
            self.chk_auto_exposure.setChecked(auto_on)
            self.slider_exposure.setEnabled(not auto_on)

        self.slider_brightness.blockSignals(False)
        self.slider_contrast.blockSignals(False)
        self.slider_saturation.blockSignals(False)
        self.slider_exposure.blockSignals(False)
        self.chk_auto_exposure.blockSignals(False)

    def update_supported_controls(self, controls: Dict[str, UvcControl]) -> None:
        """Update slider ranges or enable/disable based on actual hardware capability."""
        focus_ctrl = controls.get("focus")
        focus_supported = focus_ctrl is not None and focus_ctrl.is_supported
        self.slider_focus.setEnabled(focus_supported)
        self.chk_autofocus.setEnabled(focus_supported)

        exp_ctrl = controls.get("exposure")
        exp_supported = exp_ctrl is not None and exp_ctrl.is_supported
        self.chk_auto_exposure.setEnabled(exp_supported)
        if exp_supported:
            self.slider_exposure.setEnabled(not self.chk_auto_exposure.isChecked())

        # Initialize sliders from verified hardware values
        current_vals = {}
        for name, ctrl in controls.items():
            if ctrl.is_supported:
                current_vals[name] = ctrl.current_val
        if current_vals:
            self.apply_control_values(current_vals)

