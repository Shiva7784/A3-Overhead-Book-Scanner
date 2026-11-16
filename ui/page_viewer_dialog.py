"""High-resolution full-screen page viewer with interactive zoom, pan, and page navigation."""
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPixmap, QWheelEvent, QKeyEvent, QPainter, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QSizePolicy,
)

from services.session_manager import ScannedPage


class ZoomableImageLabel(QLabel):
    """Interactive canvas that supports mouse-drag panning and wheel zoom."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setScaledContents(False)
        self._pixmap: Optional[QPixmap] = None
        self._scale_factor: float = 1.0
        self._drag_start = QPointF()
        self._is_dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position()
            self._is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._is_dragging:
            delta = event.position() - self._drag_start
            self._drag_start = event.position()
            # Scroll parent scroll area accordingly
            sa = self.parentWidget()
            while sa and not isinstance(sa, QScrollArea):
                sa = sa.parentWidget()
            if isinstance(sa, QScrollArea):
                h_bar = sa.horizontalScrollBar()
                v_bar = sa.verticalScrollBar()
                h_bar.setValue(int(h_bar.value() - delta.x()))
                v_bar.setValue(int(v_bar.value() - delta.y()))
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self._scale_factor = 1.0
        self._update_display()

    def set_zoom(self, scale: float) -> None:
        self._scale_factor = max(0.1, min(6.0, scale))
        self._update_display()

    def zoom_in(self) -> None:
        self.set_zoom(self._scale_factor * 1.25)

    def zoom_out(self) -> None:
        self.set_zoom(self._scale_factor / 1.25)

    def fit_to_size(self, target_w: int, target_h: int) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return
        pw = self._pixmap.width()
        ph = self._pixmap.height()
        if pw <= 0 or ph <= 0:
            return
        scale_w = (target_w - 20) / float(pw)
        scale_h = (target_h - 20) / float(ph)
        self.set_zoom(min(scale_w, scale_h))

    def _update_display(self) -> None:
        if not self._pixmap or self._pixmap.isNull():
            self.clear()
            return
        new_w = int(self._pixmap.width() * self._scale_factor)
        new_h = int(self._pixmap.height() * self._scale_factor)
        scaled = self._pixmap.scaled(
            new_w,
            new_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.resize(scaled.size())


class PageViewerDialog(QDialog):
    """Full-screen / modal high-resolution document viewer for inspected captures."""

    def __init__(self, pages: List[ScannedPage], initial_index: int = 0, parent=None):
        super().__init__(parent)
        self.pages = pages
        self.current_index = max(0, min(initial_index, len(pages) - 1)) if pages else 0

        self.setWindowTitle("Captured Page Preview - High Resolution Viewer")
        self.resize(1200, 850)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1013;
                color: #e2e8f0;
            }
            QPushButton {
                background-color: #272932;
                color: #f1f5f9;
                border: 1px solid #3e414e;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3b82f6;
                border-color: #60a5fa;
            }
            QPushButton:disabled {
                background-color: #1a1b1f;
                color: #475569;
                border-color: #27272a;
            }
        """)

        self._init_ui()
        self._load_current_page()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # Top Control Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_prev = QPushButton("◀ Previous (←)")
        self.btn_prev.clicked.connect(self._prev_page)
        toolbar.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Next (→) ▶")
        self.btn_next.clicked.connect(self._next_page)
        toolbar.addWidget(self.btn_next)

        toolbar.addSpacing(16)

        self.lbl_info = QLabel("Page 1 of 1")
        self.lbl_info.setStyleSheet("font-weight: 600; color: #93c5fd; font-size: 13px;")
        toolbar.addWidget(self.lbl_info)

        toolbar.addStretch()

        self.btn_zoom_in = QPushButton("Zoom In (+)")
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        toolbar.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("Zoom Out (-)")
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        toolbar.addWidget(self.btn_zoom_out)

        self.btn_fit = QPushButton("Fit to Window")
        self.btn_fit.clicked.connect(self._fit_to_window)
        toolbar.addWidget(self.btn_fit)

        self.btn_100 = QPushButton("100% Actual")
        self.btn_100.clicked.connect(self._100_percent)
        toolbar.addWidget(self.btn_100)

        toolbar.addSpacing(12)

        self.btn_fullscreen = QPushButton("⛶ Fullscreen")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        toolbar.addWidget(self.btn_fullscreen)

        self.btn_close = QPushButton("✕ Close (Esc)")
        self.btn_close.clicked.connect(self.accept)
        toolbar.addWidget(self.btn_close)

        layout.addLayout(toolbar)

        # Central Zoomable Scroll Area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #2e3038; background-color: #0b0c0e; }")
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = ZoomableImageLabel(self)
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area, stretch=1)

        # Keyboard shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._next_page)
        QShortcut(QKeySequence(Qt.Key.Key_Plus), self, self._zoom_in)
        QShortcut(QKeySequence(Qt.Key.Key_Equal), self, self._zoom_in)
        QShortcut(QKeySequence(Qt.Key.Key_Minus), self, self._zoom_out)
        QShortcut(QKeySequence(Qt.Key.Key_F), self, self._toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.accept)

    def _load_current_page(self) -> None:
        if not self.pages or not (0 <= self.current_index < len(self.pages)):
            self.image_label.clear()
            self.lbl_info.setText("No pages available.")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            return

        page = self.pages[self.current_index]
        file_path = page.file_path

        if file_path.exists():
            pix = QPixmap(str(file_path))
            self.image_label.set_pixmap(pix)
            self._fit_to_window()

            res_str = f"{pix.width()}x{pix.height()}" if not pix.isNull() else "Unknown"
            self.lbl_info.setText(
                f"Page {self.current_index + 1} of {len(self.pages)}  |  {res_str}  |  {file_path.name}"
            )
        else:
            self.image_label.clear()
            self.lbl_info.setText(f"File not found: {file_path.name}")

        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < len(self.pages) - 1)

    def _prev_page(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self._load_current_page()

    def _next_page(self) -> None:
        if self.current_index < len(self.pages) - 1:
            self.current_index += 1
            self._load_current_page()

    def _zoom_in(self) -> None:
        self.image_label.zoom_in()

    def _zoom_out(self) -> None:
        self.image_label.zoom_out()

    def _fit_to_window(self) -> None:
        vp = self.scroll_area.viewport()
        self.image_label.fit_to_size(vp.width(), vp.height())

    def _100_percent(self) -> None:
        self.image_label.set_zoom(1.0)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.btn_fullscreen.setText("⛶ Fullscreen")
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText("⛶ Exit Fullscreen")
        self._fit_to_window()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom in or out using Ctrl+Wheel or normal mouse wheel."""
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom_in()
        elif delta < 0:
            self._zoom_out()
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Re-fit image comfortably on resize
        self._fit_to_window()
