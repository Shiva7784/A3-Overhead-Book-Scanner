"""Central live preview canvas with interactive document corner handles."""
from typing import Optional
import numpy as np
from PySide6.QtCore import Qt, QPointF, Signal, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QImage, QPixmap, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from utils.image_utils import cv_mat_to_qimage


class InteractivePreviewCanvas(QWidget):
    """Viewport displaying live stream with interactive corner overlay."""

    corners_changed = Signal(np.ndarray)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setStyleSheet("background-color: #0f1013;")

        self._current_qimage: Optional[QImage] = None
        self._raw_image_shape: Optional[tuple] = None  # (height, width)
        
        # Corners in normalized coordinates (0.0 to 1.0)
        # Order: TL, TR, BR, BL
        self._normalized_corners = np.array([
            [0.1, 0.1],
            [0.9, 0.1],
            [0.9, 0.9],
            [0.1, 0.9],
        ], dtype=np.float32)

        self._show_overlay = True
        self._show_spine = True
        self._spine_ratio = 0.5
        self._dragged_corner_idx: Optional[int] = None
        self._handle_radius = 9

        self.setMouseTracking(True)

    def clear(self) -> None:
        """Clear canvas and return to standby state."""
        self._current_qimage = None
        self._raw_image_shape = None
        self._dragged_corner_idx = None
        self.update()

    def update_frame(self, mat: np.ndarray) -> None:
        """Receive live BGR OpenCV frame from camera worker."""
        if mat is None:
            return
        self._raw_image_shape = mat.shape[:2]
        self._current_qimage = cv_mat_to_qimage(mat)
        self.update()

    def set_detected_corners(self, raw_pts: np.ndarray) -> None:
        """Update corner coordinates from auto-detector."""
        if raw_pts is None or self._raw_image_shape is None:
            return
        h, w = self._raw_image_shape
        # Normalize to [0, 1] range
        norm_pts = np.copy(raw_pts).astype(np.float32)
        norm_pts[:, 0] /= float(w)
        norm_pts[:, 1] /= float(h)
        self._normalized_corners = np.clip(norm_pts, 0.0, 1.0)
        self.update()

    def get_actual_corners(self) -> Optional[np.ndarray]:
        """Convert normalized corner points back to raw frame pixels."""
        if self._raw_image_shape is None:
            return None
        h, w = self._raw_image_shape
        pts = np.copy(self._normalized_corners)
        pts[:, 0] *= w
        pts[:, 1] *= h
        return pts

    def reset_corners(self) -> None:
        """Reset corners to default inner frame margin."""
        self._normalized_corners = np.array([
            [0.1, 0.1],
            [0.9, 0.1],
            [0.9, 0.9],
            [0.1, 0.9],
        ], dtype=np.float32)
        self.update()

    def set_overlay_visible(self, visible: bool) -> None:
        self._show_overlay = visible
        self.update()

    def set_spine_visible(self, visible: bool) -> None:
        self._show_spine = visible
        self.update()

    def set_spine_ratio(self, ratio: float) -> None:
        """Update horizontal position of the center spine line (0.2 to 0.8)."""
        self._spine_ratio = float(np.clip(ratio, 0.2, 0.8))
        self.update()

    def _get_draw_rect(self) -> QRectF:
        """Calculate aspect-ratio-corrected bounding box for image within widget."""
        if not self._current_qimage or self._current_qimage.isNull():
            return QRectF(0, 0, self.width(), self.height())

        img_w = self._current_qimage.width()
        img_h = self._current_qimage.height()
        view_w = self.width()
        view_h = self.height()

        aspect_img = img_w / float(img_h)
        aspect_view = view_w / float(view_h)

        if aspect_img > aspect_view:
            target_w = view_w
            target_h = view_w / aspect_img
        else:
            target_h = view_h
            target_w = view_h * aspect_img

        x = (view_w - target_w) / 2.0
        y = (view_h - target_h) / 2.0
        return QRectF(x, y, target_w, target_h)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        draw_rect = self._get_draw_rect()

        # 1. Draw Image or Standby Pattern
        if self._current_qimage and not self._current_qimage.isNull():
            painter.drawImage(draw_rect, self._current_qimage)
        else:
            # Standby placeholder
            painter.fillRect(self.rect(), QColor("#121316"))
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 13))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Camera Stream Offline\nSelect a camera source and click 'Connect'",
            )
            return

        # 2. Draw Interactive Overlay
        if self._show_overlay:
            self._draw_corner_overlay(painter, draw_rect)

    def _draw_corner_overlay(self, painter: QPainter, draw_rect: QRectF) -> None:
        # Convert normalized points to widget coordinates
        pts_widget = []
        for nx, ny in self._normalized_corners:
            wx = draw_rect.left() + nx * draw_rect.width()
            wy = draw_rect.top() + ny * draw_rect.height()
            pts_widget.append(QPointF(wx, wy))

        # Draw green bounding polygon for detected page boundary
        pen = QPen(QColor(34, 197, 94, 230), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(34, 197, 94, 40)))
        painter.drawPolygon(pts_widget)

        # Draw book spine guide if dual-page mode enabled
        if self._show_spine:
            top_mid = pts_widget[0] + (pts_widget[1] - pts_widget[0]) * self._spine_ratio
            bot_mid = pts_widget[3] + (pts_widget[2] - pts_widget[3]) * self._spine_ratio
            spine_pen = QPen(QColor(245, 158, 11, 230), 2, Qt.PenStyle.DashDotLine)
            painter.setPen(spine_pen)
            painter.drawLine(top_mid, bot_mid)

        # Draw corner grab handles
        corner_labels = ["TL", "TR", "BR", "BL"]
        for idx, pt in enumerate(pts_widget):
            # Outer ring & green fill
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QBrush(QColor(22, 163, 74)))
            painter.drawEllipse(pt, self._handle_radius, self._handle_radius)

            # Label corner
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(
                QRectF(pt.x() - 15, pt.y() - 25, 30, 15),
                Qt.AlignmentFlag.AlignCenter,
                corner_labels[idx],
            )

    def mousePressEvent(self, event) -> None:
        if self._current_qimage is None or not self._show_overlay or event.button() != Qt.MouseButton.LeftButton:
            return

        draw_rect = self._get_draw_rect()
        pos = event.position()

        # Check proximity to any handle
        for idx, (nx, ny) in enumerate(self._normalized_corners):
            wx = draw_rect.left() + nx * draw_rect.width()
            wy = draw_rect.top() + ny * draw_rect.height()
            dist = np.hypot(pos.x() - wx, pos.y() - wy)
            if dist <= self._handle_radius * 2:
                self._dragged_corner_idx = idx
                break

    def mouseMoveEvent(self, event) -> None:
        if self._current_qimage is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        draw_rect = self._get_draw_rect()
        pos = event.position()

        if self._dragged_corner_idx is not None:
            # Update position of dragged corner
            nx = (pos.x() - draw_rect.left()) / max(1.0, draw_rect.width())
            ny = (pos.y() - draw_rect.top()) / max(1.0, draw_rect.height())
            self._normalized_corners[self._dragged_corner_idx] = [
                np.clip(nx, 0.0, 1.0),
                np.clip(ny, 0.0, 1.0),
            ]
            self.update()
            if self._raw_image_shape:
                self.corners_changed.emit(self.get_actual_corners())
        else:
            # Change cursor if hovering near a handle
            hover = False
            for nx, ny in self._normalized_corners:
                wx = draw_rect.left() + nx * draw_rect.width()
                wy = draw_rect.top() + ny * draw_rect.height()
                if np.hypot(pos.x() - wx, pos.y() - wy) <= self._handle_radius * 2:
                    hover = True
                    break
            self.setCursor(Qt.CursorShape.PointingHandCursor if hover else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        self._dragged_corner_idx = None


class PreviewPanel(QWidget):
    """Central container wrapping the canvas and top/bottom metadata ribbons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Top banner
        self.lbl_info = QLabel("Live 4K Preview | Overhead A3 Service Register Digitizer")
        self.lbl_info.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 2px 4px;")
        layout.addWidget(self.lbl_info)

        # Interactive Canvas
        self.canvas = InteractivePreviewCanvas(self)
        layout.addWidget(self.canvas, stretch=1)

    def clear_preview(self) -> None:
        """Clear canvas and reset info ribbon to standby."""
        self.canvas.clear()
        self.lbl_info.setText("Live Preview | Standby (Camera Offline)")


