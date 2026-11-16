"""Bottom gallery panel displaying captured page thumbnails and PDF export triggers."""
from typing import List
from PySide6.QtCore import Signal, QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from services.session_manager import ScannedPage


class GalleryPanel(QWidget):
    """Bottom thumbnail gallery displaying captured pages in the current session."""

    export_pdf_requested = Signal()
    delete_page_requested = Signal(int)
    move_left_requested = Signal(int)
    move_right_requested = Signal(int)
    page_selected = Signal(int)
    page_view_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(175)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 8)
        layout.setSpacing(6)

        # Header Ribbon
        header_layout = QHBoxLayout()
        self.lbl_page_count = QLabel("Captured Pages (0)")
        self.lbl_page_count.setStyleSheet("font-weight: 600; color: #f1f5f9;")
        header_layout.addWidget(self.lbl_page_count)

        header_layout.addStretch()

        self.btn_view = QPushButton("🔍 Preview Page")
        self.btn_view.setToolTip("View full-resolution scanned page in detail (or click thumbnail)")
        self.btn_view.setEnabled(False)
        self.btn_view.clicked.connect(self._on_view)
        header_layout.addWidget(self.btn_view)

        self.btn_move_left = QPushButton("◀ Move Left")
        self.btn_move_left.setEnabled(False)
        self.btn_move_left.clicked.connect(self._on_move_left)
        header_layout.addWidget(self.btn_move_left)

        self.btn_move_right = QPushButton("Move Right ▶")
        self.btn_move_right.setEnabled(False)
        self.btn_move_right.clicked.connect(self._on_move_right)
        header_layout.addWidget(self.btn_move_right)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete)
        header_layout.addWidget(self.btn_delete)

        self.btn_export_pdf = QPushButton("📑 EXPORT TO PDF")
        self.btn_export_pdf.setObjectName("successActionBtn")
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_pdf.clicked.connect(self.export_pdf_requested.emit)
        header_layout.addWidget(self.btn_export_pdf)

        layout.addLayout(header_layout)

        # Horizontal Thumbnail Strip
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(130, 95))
        self.list_widget.setMovement(QListWidget.Movement.Static)
        self.list_widget.setSpacing(8)
        self.list_widget.setFlow(QListWidget.Flow.LeftToRight)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def refresh_gallery(self, pages: List[ScannedPage]) -> None:
        """Repopulate thumbnail strip with current scanned pages."""
        current_idx = self.list_widget.currentRow()
        self.list_widget.clear()

        for page in pages:
            item = QListWidgetItem()
            item.setText(f"Page {page.page_number}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)

            if page.thumbnail_path and page.thumbnail_path.exists():
                pix = QPixmap(str(page.thumbnail_path))
                item.setIcon(QIcon(pix))
            elif page.file_path.exists():
                pix = QPixmap(str(page.file_path))
                item.setIcon(QIcon(pix))

            self.list_widget.addItem(item)

        total = len(pages)
        self.lbl_page_count.setText(f"Captured Pages ({total})")
        self.btn_export_pdf.setEnabled(total > 0)

        # Restore selection if valid
        if 0 <= current_idx < total:
            self.list_widget.setCurrentRow(current_idx)
        elif total > 0:
            self.list_widget.setCurrentRow(total - 1)
        else:
            self._update_button_states(-1)

    def _on_row_changed(self, row: int) -> None:
        self._update_button_states(row)
        if row >= 0:
            self.page_selected.emit(row)

    def _update_button_states(self, row: int) -> None:
        total = self.list_widget.count()
        has_sel = 0 <= row < total
        self.btn_view.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)
        self.btn_move_left.setEnabled(has_sel and row > 0)
        self.btn_move_right.setEnabled(has_sel and row < total - 1)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        row = self.list_widget.row(item)
        if row >= 0:
            self.page_view_requested.emit(row)

    def _on_view(self) -> None:
        row = self.list_widget.currentRow()
        if row >= 0:
            self.page_view_requested.emit(row)

    def _on_move_left(self) -> None:
        row = self.list_widget.currentRow()
        if row > 0:
            self.move_left_requested.emit(row)

    def _on_move_right(self) -> None:
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count() - 1:
            self.move_right_requested.emit(row)

    def _on_delete(self) -> None:
        row = self.list_widget.currentRow()
        if row >= 0:
            self.delete_page_requested.emit(row)

