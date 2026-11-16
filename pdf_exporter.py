"""PDF generation service using img2pdf."""
import logging
from pathlib import Path
from typing import List, Optional
import img2pdf
from PIL import Image

logger = logging.getLogger(__name__)


class PdfExporter:
    """Exports scanned high-resolution pages into a unified multi-page PDF document."""

    @staticmethod
    def export_pages(
        image_paths: List[Path],
        output_pdf_path: Path,
        title: Optional[str] = "Service Register Scan",
        dpi: int = 300,
    ) -> bool:
        """Convert a list of image files into a single multi-page PDF document.
        
        Preserves original resolution without lossy re-encoding.
        Handles empty sessions and invalid image files gracefully.
        """
        if not image_paths:
            logger.warning("No image paths provided for PDF export.")
            return False

        output_pdf_path = Path(output_pdf_path)
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

        valid_paths = []
        for p in image_paths:
            path_obj = Path(p)
            if not path_obj.exists():
                logger.warning(f"Image file does not exist: {path_obj}")
                continue
            # Validate image integrity
            try:
                with Image.open(path_obj) as img:
                    img.verify()
                valid_paths.append(str(path_obj))
            except Exception as e:
                logger.warning(f"Skipping unreadable or corrupted image {path_obj}: {e}")

        if not valid_paths:
            logger.error("No valid image files available to compile into PDF.")
            return False

        try:
            layout_fun = img2pdf.default_layout_fun
            with open(output_pdf_path, "wb") as f:
                pdf_bytes = img2pdf.convert(
                    valid_paths,
                    layout_fun=layout_fun,
                    title=title,
                    producer="A3 Overhead Book Scanner",
                )
                f.write(pdf_bytes)

            return output_pdf_path.exists() and output_pdf_path.stat().st_size > 0
        except Exception as e:
            logger.exception(f"Error compiling PDF: {e}")
            return False
