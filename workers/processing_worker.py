"""Background worker for asynchronous document processing and PDF compilation."""
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from PySide6.QtCore import QThread, Signal

from processor import DocumentProcessor
from pdf_exporter import PdfExporter


class ProcessingWorker(QThread):
    """Executes heavy image warp and PDF export without freezing the UI."""

    export_finished = Signal(bool, str)
    process_finished = Signal(object)  # Processed images tuple: (left, right) or (single,)
    progress = Signal(int, str)

    def __init__(
        self,
        task_type: str,
        image: Optional[np.ndarray] = None,
        pts: Optional[np.ndarray] = None,
        split_dual: bool = True,
        spine_ratio: float = 0.5,
        enhancement_mode: str = "Original Color",
        pdf_image_paths: Optional[List[Path]] = None,
        pdf_output_path: Optional[Path] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.task_type = task_type
        self.image = image
        self.pts = pts
        self.split_dual = split_dual
        self.spine_ratio = spine_ratio
        self.enhancement_mode = enhancement_mode
        self.pdf_image_paths = pdf_image_paths or []
        self.pdf_output_path = pdf_output_path

    def run(self) -> None:
        if self.task_type == "process_capture":
            self._handle_processing()
        elif self.task_type == "export_pdf":
            self._handle_pdf_export()

    def _handle_processing(self) -> None:
        if self.image is None:
            self.process_finished.emit(None)
            return

        self.progress.emit(20, "Applying perspective transformation...")
        if self.pts is not None:
            warped = DocumentProcessor.four_point_transform(self.image, self.pts)
        else:
            warped = self.image

        self.progress.emit(60, f"Enhancing document ({self.enhancement_mode})...")
        enhanced = DocumentProcessor.enhance_document(warped, self.enhancement_mode)

        if self.split_dual:
            self.progress.emit(85, "Splitting dual-page spread...")
            left, right = DocumentProcessor.split_spread(
                enhanced, spine_ratio=self.spine_ratio
            )
            self.progress.emit(100, "Done")
            self.process_finished.emit((left, right))
        else:
            self.progress.emit(100, "Done")
            self.process_finished.emit((enhanced,))

    def _handle_pdf_export(self) -> None:
        if not self.pdf_output_path or not self.pdf_image_paths:
            self.export_finished.emit(False, "No images or output path specified.")
            return

        self.progress.emit(30, "Compiling multi-page lossless PDF...")
        try:
            success = PdfExporter.export_pages(
                self.pdf_image_paths, self.pdf_output_path
            )
            if success:
                self.progress.emit(100, "Export completed.")
                self.export_finished.emit(True, str(self.pdf_output_path))
            else:
                self.export_finished.emit(False, "Failed to compile PDF.")
        except Exception as e:
            self.export_finished.emit(False, str(e))
