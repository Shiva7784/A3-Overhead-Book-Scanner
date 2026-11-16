"""Main window implementation for the A3 Overhead Book Scanner."""
from pathlib import Path
from typing import Optional
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QStatusBar,
    QLabel,
)
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from config.settings import TEST_IMAGES_DIR, SCANS_DIR
from camera import PhysicalUvcCamera, MockFolderCamera, NetworkStreamCamera, BaseCamera
from workers.camera_worker import CameraWorker
from workers.processing_worker import ProcessingWorker
from services.session_manager import SessionManager
from processor import DocumentProcessor
from ui.camera_panel import CameraPanel
from ui.preview_panel import PreviewPanel
from ui.processing_panel import ProcessingPanel
from ui.gallery_panel import GalleryPanel
from ui.page_viewer_dialog import PageViewerDialog


class MainWindow(QMainWindow):
    """Main application window uniting all camera, vision, and session components."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("A3 Overhead Book Scanner - Professional Edition")
        self.resize(1440, 920)
        self.setMinimumSize(1100, 700)

        # Core State & Services
        self.session_manager = SessionManager(SCANS_DIR)
        self.active_camera: Optional[BaseCamera] = None
        self.camera_worker: Optional[CameraWorker] = None
        self.processing_worker: Optional[ProcessingWorker] = None
        self._current_raw_frame: Optional[np.ndarray] = None
        self._auto_detect_counter = 0

        self._init_ui()
        self._init_menus()
        self._init_shortcuts()
        self._init_signals()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        # Vertical Splitter: Upper Workspace vs Lower Gallery
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)

        # Upper Workspace (Horizontal Splitter: Left Controls | Central Preview | Right Processing)
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.camera_panel = CameraPanel(self)
        self.preview_panel = PreviewPanel(self)
        self.processing_panel = ProcessingPanel(self)

        self.h_splitter.addWidget(self.camera_panel)
        self.h_splitter.addWidget(self.preview_panel)
        self.h_splitter.addWidget(self.processing_panel)

        # Initial horizontal proportions (approx 20% | 60% | 20%)
        self.h_splitter.setStretchFactor(0, 0)
        self.h_splitter.setStretchFactor(1, 1)
        self.h_splitter.setStretchFactor(2, 0)

        # Lower Gallery Panel
        self.gallery_panel = GalleryPanel(self)

        self.v_splitter.addWidget(self.h_splitter)
        self.v_splitter.addWidget(self.gallery_panel)
        self.v_splitter.setStretchFactor(0, 1)
        self.v_splitter.setStretchFactor(1, 0)

        root_layout.addWidget(self.v_splitter)

        # Professional Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.lbl_status_msg = QLabel("Ready")
        self.lbl_fps = QLabel("FPS: --")
        self.lbl_res = QLabel("Resolution: --")
        self.lbl_backend = QLabel("Backend: Idle")

        self.status_bar.addWidget(self.lbl_status_msg, stretch=1)
        self.status_bar.addPermanentWidget(self.lbl_res)
        self.status_bar.addPermanentWidget(self.lbl_fps)
        self.status_bar.addPermanentWidget(self.lbl_backend)

    def _init_menus(self) -> None:
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        action_new_session = QAction("&New Session", self)
        action_new_session.setShortcut(QKeySequence.StandardKey.New)
        action_new_session.triggered.connect(self._on_new_session)
        file_menu.addAction(action_new_session)

        action_export_pdf = QAction("&Export PDF...", self)
        action_export_pdf.setShortcut(QKeySequence("Ctrl+E"))
        action_export_pdf.triggered.connect(self._on_export_pdf)
        file_menu.addAction(action_export_pdf)

        file_menu.addSeparator()

        action_open_scans = QAction("&Open Scans Directory", self)
        action_open_scans.triggered.connect(self._on_open_scans_folder)
        file_menu.addAction(action_open_scans)

        file_menu.addSeparator()

        action_exit = QAction("E&xit", self)
        action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        # Camera Menu
        cam_menu = menu_bar.addMenu("&Camera")
        action_toggle_cam = QAction("&Toggle Connect", self)
        action_toggle_cam.triggered.connect(self.camera_panel._toggle_connection)
        cam_menu.addAction(action_toggle_cam)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        action_about = QAction("&About A3 Book Scanner", self)
        action_about.triggered.connect(self._on_about)
        help_menu.addAction(action_about)

    def _init_shortcuts(self) -> None:
        # Space: Capture
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.shortcut_space.activated.connect(self._on_capture_shortcut)

        # Return / Enter: also Capture
        self.shortcut_enter = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self.shortcut_enter.activated.connect(self._on_capture_shortcut)

        # Z: Undo last capture
        self.shortcut_undo = QShortcut(QKeySequence(Qt.Key.Key_Z), self)
        self.shortcut_undo.activated.connect(self._on_undo_shortcut)

        # S: Toggle Single / Dual Page mode
        self.shortcut_split = QShortcut(QKeySequence(Qt.Key.Key_S), self)
        self.shortcut_split.activated.connect(self._on_toggle_split_shortcut)

        # M: Cycle through enhancement modes
        self.shortcut_mode = QShortcut(QKeySequence(Qt.Key.Key_M), self)
        self.shortcut_mode.activated.connect(self._on_cycle_enhancement_shortcut)

        # P: Export current session PDF
        self.shortcut_pdf = QShortcut(QKeySequence(Qt.Key.Key_P), self)
        self.shortcut_pdf.activated.connect(self._on_export_pdf_shortcut)

    def _is_text_input_active(self) -> bool:
        """Check if user is currently typing in an input field."""
        from PySide6.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit
        focus_w = self.focusWidget()
        return isinstance(focus_w, (QLineEdit, QTextEdit, QPlainTextEdit))

    def _on_capture_shortcut(self) -> None:
        if not self._is_text_input_active():
            self._on_capture()

    def _on_undo_shortcut(self) -> None:
        if not self._is_text_input_active():
            self._on_undo_capture()

    def _on_toggle_split_shortcut(self) -> None:
        if not self._is_text_input_active():
            is_dual = self.processing_panel.toggle_dual_page_mode()
            mode_desc = "Dual-Page Mode (A3 -> 2x A4)" if is_dual else "Single-Page Mode"
            self.lbl_status_msg.setText(f"Toggled split mode: {mode_desc}")

    def _on_cycle_enhancement_shortcut(self) -> None:
        if not self._is_text_input_active():
            mode_name = self.processing_panel.cycle_enhancement_mode()
            self.lbl_status_msg.setText(f"Enhancement mode: {mode_name}")

    def _on_export_pdf_shortcut(self) -> None:
        if not self._is_text_input_active():
            self._on_export_pdf()

    def _on_undo_capture(self) -> None:
        """Remove and delete the files of the most recent capture batch."""
        removed = self.session_manager.undo_last_capture()
        if removed:
            self.gallery_panel.refresh_gallery(self.session_manager.get_pages())
            total = len(self.session_manager.get_pages())
            self.lbl_status_msg.setText(
                f"Undid last capture (removed {len(removed)} page(s)). Total remaining: {total}"
            )
        else:
            self.lbl_status_msg.setText("No captured pages to undo.")

    def _init_signals(self) -> None:
        # Camera Panel Signals
        self.camera_panel.connect_requested.connect(self._start_camera)
        self.camera_panel.disconnect_requested.connect(self._stop_camera)
        self.camera_panel.control_changed.connect(self._on_camera_control_changed)
        self.camera_panel.reset_controls_requested.connect(self._on_reset_camera_controls)

        # Processing Panel Signals
        self.processing_panel.capture_requested.connect(self._on_capture)
        self.processing_panel.detect_boundary_requested.connect(self._trigger_boundary_detection)
        self.processing_panel.reset_corners_requested.connect(self.preview_panel.canvas.reset_corners)
        self.processing_panel.chk_show_overlay.toggled.connect(self.preview_panel.canvas.set_overlay_visible)
        self.processing_panel.dual_split_changed.connect(self.preview_panel.canvas.set_spine_visible)
        self.processing_panel.spine_ratio_changed.connect(self.preview_panel.canvas.set_spine_ratio)
        self.preview_panel.canvas.set_spine_ratio(self.processing_panel.get_spine_ratio())

        # Gallery Panel Signals
        self.gallery_panel.export_pdf_requested.connect(self._on_export_pdf)
        self.gallery_panel.delete_page_requested.connect(self._on_delete_page)
        self.gallery_panel.move_left_requested.connect(self._on_move_page_left)
        self.gallery_panel.move_right_requested.connect(self._on_move_page_right)
        self.gallery_panel.page_view_requested.connect(self._on_view_page)

    def _start_camera(
        self,
        mode: str,
        device_index: int,
        target_w: int = 3840,
        target_h: int = 2160,
        stream_url: str = "",
    ) -> None:
        self._stop_camera()

        self.lbl_status_msg.setText("Connecting to camera stream...")

        if mode == "mock":
            self.active_camera = MockFolderCamera(
                TEST_IMAGES_DIR, width=target_w, height=target_h
            )
        elif mode == "ip":
            self.active_camera = NetworkStreamCamera(stream_url=stream_url)
        else:
            self.active_camera = PhysicalUvcCamera(
                device_index=device_index,
                target_width=target_w,
                target_height=target_h,
            )

        self.camera_worker = CameraWorker(self.active_camera)
        self.camera_worker.frame_ready.connect(self._on_frame_received)
        self.camera_worker.fps_updated.connect(self._on_fps_updated)
        self.camera_worker.error_occurred.connect(self._on_camera_error)
        self.camera_worker.connection_changed.connect(self._on_camera_connection_changed)
        self.camera_worker.start()

    def _stop_camera(self) -> None:
        if self.camera_worker:
            # Disconnect signals to avoid stale signals during worker teardown
            try:
                self.camera_worker.frame_ready.disconnect()
            except Exception:
                pass
            try:
                self.camera_worker.fps_updated.disconnect()
            except Exception:
                pass
            try:
                self.camera_worker.error_occurred.disconnect()
            except Exception:
                pass
            try:
                self.camera_worker.connection_changed.disconnect()
            except Exception:
                pass

            self.camera_worker.stop()
            self.camera_worker = None

        if self.active_camera:
            self.active_camera.close()
            self.active_camera = None

        self._current_raw_frame = None

        # Reset preview canvas and remove frozen frame
        self.preview_panel.clear_preview()

        self.camera_panel.set_connected_state(False)
        self.lbl_status_msg.setText("Camera disconnected.")
        self.lbl_fps.setText("FPS: --")
        self.lbl_res.setText("Resolution: --")
        self.lbl_backend.setText("Backend: Idle")

    def _on_camera_connection_changed(self, connected: bool) -> None:
        if connected and self.active_camera:
            caps = self.active_camera.get_capabilities()
            if caps:
                info_text = f"Driver: {caps.backend}\nNegotiated: {caps.width}x{caps.height}\nNominal: {caps.fps:.1f} fps"
                self.lbl_res.setText(f"{caps.width}x{caps.height}")
                self.lbl_backend.setText(caps.backend)
                self.preview_panel.lbl_info.setText(
                    f"Live Feed: {caps.width}x{caps.height} @ {caps.fps:.0f} FPS | Overhead A3 Service Register Digitizer"
                )
            else:
                info_text = "Connected"
            self.camera_panel.set_connected_state(True, info_text)
            self.camera_panel.update_supported_controls(self.active_camera.get_controls())
            self.lbl_status_msg.setText("Camera active.")
        else:
            self._stop_camera()

    def _on_reset_camera_controls(self) -> None:
        """Reset hardware controls to factory calibrated defaults."""
        if self.active_camera:
            defaults = self.active_camera.reset_controls()
            self.camera_panel.apply_control_values(defaults)
            self.lbl_status_msg.setText("Camera hardware controls reset to calibrated defaults.")

    def _on_camera_error(self, message: str) -> None:
        self.lbl_status_msg.setText(f"Camera Error: {message}")
        QMessageBox.warning(self, "Camera Warning", message)

    def _on_frame_received(self, frame: np.ndarray) -> None:
        self._current_raw_frame = frame
        self.preview_panel.canvas.update_frame(frame)

        # Run boundary auto-detector periodically (every ~30 frames) if enabled
        if self.processing_panel.chk_auto_detect.isChecked():
            self._auto_detect_counter += 1
            if self._auto_detect_counter >= 30:
                self._auto_detect_counter = 0
                self._trigger_boundary_detection()

    def _on_fps_updated(self, fps: float) -> None:
        self.lbl_fps.setText(f"FPS: {fps:.1f}")

    def _on_camera_control_changed(self, name: str, value: float) -> None:
        if self.active_camera:
            self.active_camera.set_control(name, value)

    def _trigger_boundary_detection(self) -> None:
        if self._current_raw_frame is None:
            return
        pts = DocumentProcessor.detect_page_boundary(self._current_raw_frame)
        if pts is not None:
            self.preview_panel.canvas.set_detected_corners(pts)
            self.lbl_status_msg.setText("Document boundary detected.")

    def _on_capture(self) -> None:
        if not self.active_camera or not self.active_camera.is_opened():
            QMessageBox.information(
                self,
                "Camera Offline",
                "Please connect a physical camera or switch to Mock Folder mode first.",
            )
            return

        if self.processing_worker and self.processing_worker.isRunning():
            return  # Already processing previous capture

        self.processing_panel.set_processing(True, "Grabbing full 4K frame...", 10)

        # Grab full unscaled 4K frame directly from camera
        ret, frame_4k = self.active_camera.capture_frame()
        if not ret or frame_4k is None:
            self.processing_panel.set_processing(False, "Capture failed.", 0)
            QMessageBox.critical(self, "Capture Error", "Failed to capture frame from camera.")
            return

        corners = self.preview_panel.canvas.get_actual_corners()
        split_dual = self.processing_panel.chk_split_pages.isChecked()
        mode = self.processing_panel.get_selected_enhancement_mode()
        spine_ratio = self.processing_panel.get_spine_ratio()

        self.processing_worker = ProcessingWorker(
            task_type="process_capture",
            image=frame_4k,
            pts=corners,
            split_dual=split_dual,
            spine_ratio=spine_ratio,
            enhancement_mode=mode,
            parent=self,
        )
        self.processing_worker.progress.connect(self._on_processing_progress)
        self.processing_worker.process_finished.connect(self._on_processing_completed)
        self.processing_worker.start()

    def _on_processing_progress(self, val: int, msg: str) -> None:
        self.processing_panel.set_processing(True, msg, val)
        self.lbl_status_msg.setText(msg)

    def _on_processing_completed(self, results) -> None:
        self.processing_panel.set_processing(False, "Capture saved.", 100)
        if not results:
            return

        # Add pages to session manager and record capture batch for undo support
        added = self.session_manager.add_capture_results(results)

        self.gallery_panel.refresh_gallery(self.session_manager.get_pages())
        self.lbl_status_msg.setText(f"Added {len(added)} page(s) to session. Total: {len(self.session_manager.get_pages())}")

    def _on_export_pdf(self) -> None:
        pages = self.session_manager.get_pages()
        if not pages:
            QMessageBox.information(self, "Export PDF", "No scanned pages available in the session to export.")
            return

        default_pdf_path = self.session_manager.get_default_pdf_path()
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Digitized Book to Multi-Page PDF",
            str(default_pdf_path),
            "PDF Files (*.pdf)",
        )
        if not out_path:
            return

        image_paths = [p.file_path for p in pages]
        self.processing_worker = ProcessingWorker(
            task_type="export_pdf",
            pdf_image_paths=image_paths,
            pdf_output_path=Path(out_path),
            parent=self,
        )
        self.processing_worker.progress.connect(self._on_processing_progress)
        self.processing_worker.export_finished.connect(self._on_pdf_export_finished)
        self.processing_worker.start()

    def _on_pdf_export_finished(self, success: bool, message: str) -> None:
        self.processing_panel.set_processing(False, "Export finished", 100)
        if success:
            self.lbl_status_msg.setText(f"PDF exported successfully: {message}")
            QMessageBox.information(self, "Export Successful", f"PDF exported successfully to:\n{message}")
        else:
            self.lbl_status_msg.setText("PDF export failed.")
            QMessageBox.critical(self, "Export Error", f"Failed to export PDF:\n{message}")

    def _on_new_session(self) -> None:
        if self.session_manager.get_pages():
            reply = QMessageBox.question(
                self,
                "New Session",
                "Start a new scanning session? Unsaved active page references will be cleared.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.session_manager.clear()
        self.gallery_panel.refresh_gallery(self.session_manager.get_pages())
        self.lbl_status_msg.setText("Started new scanning session.")

    def _on_view_page(self, index: int) -> None:
        """Open high-resolution fullscreen preview dialog for the selected page."""
        pages = self.session_manager.get_pages()
        if not pages or not (0 <= index < len(pages)):
            return
        dialog = PageViewerDialog(pages, initial_index=index, parent=self)
        dialog.exec()

    def _on_delete_page(self, index: int) -> None:
        self.session_manager.remove_page(index)
        self.gallery_panel.refresh_gallery(self.session_manager.get_pages())
        self.lbl_status_msg.setText(f"Removed page {index + 1}.")

    def _on_move_page_left(self, index: int) -> None:
        order = list(range(len(self.session_manager.get_pages())))
        order[index], order[index - 1] = order[index - 1], order[index]
        self.session_manager.reorder_pages(order)
        self.gallery_panel.refresh_gallery(self.session_manager.get_pages())

    def _on_move_page_right(self, index: int) -> None:
        order = list(range(len(self.session_manager.get_pages())))
        order[index], order[index + 1] = order[index + 1], order[index]
        self.session_manager.reorder_pages(order)
        self.gallery_panel.refresh_gallery(self.session_manager.get_pages())

    def _on_open_scans_folder(self) -> None:
        import os
        target_dir = self.session_manager.current_session_dir
        if not target_dir.exists():
            target_dir = SCANS_DIR
        os.startfile(str(target_dir))

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About A3 Overhead Book Scanner",
            "<b>A3 Overhead Book Scanner</b><br>"
            "Professional Physical Service Register Digitizer.<br><br>"
            "Features:<br>"
            "• 4K UVC Overhead Camera Integration<br>"
            "• Automatic Document Boundary Detection<br>"
            "• Manual Interactive 4-Corner Perspective Adjustment<br>"
            "• Dual-Page Spread Splitting (A3 to 2x A4)<br>"
            "• CLAHE & Adaptive Readability Filters<br>"
            "• Direct Multi-Page Lossless PDF Compilation<br>",
        )

    def closeEvent(self, event) -> None:
        """Clean shutdown of background threads."""
        self._stop_camera()
        if self.processing_worker and self.processing_worker.isRunning():
            self.processing_worker.wait(1000)
        event.accept()

