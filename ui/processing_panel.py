"""Right sidebar panel for computer vision controls, enhancement filters, and capture trigger."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QGroupBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QSlider,
    QProgressBar,
    QScrollArea,
)
from PySide6.QtCore import Qt


class ProcessingPanel(QWidget):
    """Controls for boundary detection, dual-page splitting, enhancement, and capture trigger."""

    capture_requested = Signal()
    detect_boundary_requested = Signal()
    reset_corners_requested = Signal()
    enhancement_changed = Signal(str)
    dual_split_changed = Signal(bool)
    spine_ratio_changed = Signal(float)

    PRIMARY_MODES = [
        "Original Color",
        "Enhanced Document Color",
        "Clean Black & White",
        "Grayscale (Optional)",
    ]

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

        # 1. Capture Action Section
        capture_group = QGroupBox("Capture Control")
        cap_layout = QVBoxLayout(capture_group)
        cap_layout.setSpacing(10)

        self.btn_capture = QPushButton("📸 CAPTURE 4K SPREAD")
        self.btn_capture.setObjectName("primaryActionBtn")
        self.btn_capture.setToolTip("Capture full uncompressed 4K frame and process (Shortcut: Space)")
        self.btn_capture.clicked.connect(self.capture_requested.emit)
        cap_layout.addWidget(self.btn_capture)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        cap_layout.addWidget(self.progress_bar)

        self.lbl_process_status = QLabel("Ready for capture")
        self.lbl_process_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        cap_layout.addWidget(self.lbl_process_status)

        layout.addWidget(capture_group)

        # 2. Boundary & Perspective Section
        boundary_group = QGroupBox("Page Boundary & Geometry")
        b_layout = QVBoxLayout(boundary_group)
        b_layout.setSpacing(10)

        self.chk_auto_detect = QCheckBox("Auto-Detect Boundary")
        self.chk_auto_detect.setChecked(True)
        b_layout.addWidget(self.chk_auto_detect)

        self.btn_redetect = QPushButton("Re-Detect Corners")
        self.btn_redetect.setToolTip("Run automatic quadrilateral detector on current frame")
        self.btn_redetect.clicked.connect(self.detect_boundary_requested.emit)
        b_layout.addWidget(self.btn_redetect)

        self.btn_reset_corners = QPushButton("Reset Corner Handles")
        self.btn_reset_corners.clicked.connect(self.reset_corners_requested.emit)
        b_layout.addWidget(self.btn_reset_corners)

        self.chk_show_overlay = QCheckBox("Show Overlay Guides")
        self.chk_show_overlay.setChecked(True)
        b_layout.addWidget(self.chk_show_overlay)

        layout.addWidget(boundary_group)

        # 3. Dual-Page Book Splitting Section
        split_group = QGroupBox("Dual-Page Book Splitting")
        s_layout = QVBoxLayout(split_group)
        s_layout.setSpacing(8)

        self.chk_split_pages = QCheckBox("Split Dual Pages (A3 -> 2x A4)")
        self.chk_split_pages.setChecked(True)
        self.chk_split_pages.setToolTip("Shortcut: S")
        self.chk_split_pages.toggled.connect(self._on_split_toggled)
        s_layout.addWidget(self.chk_split_pages)

        self.lbl_spine = QLabel("Spine Center Offset (0%):")
        s_layout.addWidget(self.lbl_spine)

        self.slider_spine = QSlider(Qt.Orientation.Horizontal)
        self.slider_spine.setRange(-50, 50)
        self.slider_spine.setValue(0)
        self.slider_spine.setToolTip("Fine-tune horizontal center split position")
        self.slider_spine.valueChanged.connect(self._on_spine_slider_changed)
        s_layout.addWidget(self.slider_spine)

        layout.addWidget(split_group)

        # 4. Document Readability Enhancement Section
        enhance_group = QGroupBox("Document Enhancement")
        e_layout = QVBoxLayout(enhance_group)
        e_layout.setSpacing(8)

        e_layout.addWidget(QLabel("Enhancement Mode (Shortcut: M):"))
        self.combo_enhancement = QComboBox()
        self.combo_enhancement.addItems(self.PRIMARY_MODES)
        self.combo_enhancement.currentIndexChanged.connect(self._on_enhancement_selected)
        e_layout.addWidget(self.combo_enhancement)

        self.chk_deskew = QCheckBox("Automatic Deskew")
        self.chk_deskew.setChecked(True)
        e_layout.addWidget(self.chk_deskew)

        layout.addWidget(enhance_group)
        layout.addStretch()

        scroll_area.setWidget(container)
        outer_layout.addWidget(scroll_area)

    def _on_split_toggled(self, checked: bool) -> None:
        self.slider_spine.setEnabled(checked)
        self.lbl_spine.setEnabled(checked)
        self.dual_split_changed.emit(checked)

    def _on_spine_slider_changed(self, val: int) -> None:
        self.lbl_spine.setText(f"Spine Center Offset ({val:+d}%):")
        ratio = self.get_spine_ratio()
        self.spine_ratio_changed.emit(ratio)

    def get_spine_ratio(self) -> float:
        """Returns normalized horizontal position of center split line (approx 0.25 to 0.75)."""
        val = self.slider_spine.value()
        # val from -50 to 50 maps to 0.25 to 0.75
        return 0.5 + (val / 200.0)

    def toggle_dual_page_mode(self) -> bool:
        """Toggle between Dual Page and Single Page mode (Shortcut: S)."""
        new_state = not self.chk_split_pages.isChecked()
        self.chk_split_pages.setChecked(new_state)
        return new_state

    def cycle_enhancement_mode(self) -> str:
        """Cycle through the three primary enhancement modes (Shortcut: M)."""
        curr = self.combo_enhancement.currentIndex()
        next_idx = (curr + 1) % 3  # Cycle through top 3 primary modes
        self.combo_enhancement.setCurrentIndex(next_idx)
        return self.combo_enhancement.currentText()

    def get_selected_enhancement_mode(self) -> str:
        """Get the active enhancement mode string."""
        return self.combo_enhancement.currentText()

    def _on_enhancement_selected(self, index: int) -> None:
        mode = self.combo_enhancement.itemText(index)
        self.enhancement_changed.emit(mode)

    def set_processing(self, active: bool, status_text: str = "", progress: int = 0) -> None:
        self.btn_capture.setEnabled(not active)
        self.progress_bar.setVisible(active)
        if active:
            self.progress_bar.setValue(progress)
            self.lbl_process_status.setText(status_text or "Processing high-res capture...")
        else:
            self.lbl_process_status.setText(status_text or "Ready for capture")
