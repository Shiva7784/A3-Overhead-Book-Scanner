"""Session and scanned page lifecycle management."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np

from config.settings import SCANS_DIR


@dataclass
class ScannedPage:
    """Represents a single digitized page entry."""
    id: str
    file_path: Path
    timestamp: datetime = field(default_factory=datetime.now)
    page_number: int = 1
    width: int = 0
    height: int = 0
    thumbnail_path: Optional[Path] = None


class SessionManager:
    """Manages active scanning sessions, page ordering, and session persistence in timestamped folders."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or SCANS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_dir: Path = self._create_session_folder()
        self.pages: List[ScannedPage] = []
        self._capture_history: List[int] = []  # Stores number of pages added in each capture batch
        self._spread_index: int = 0

    def _create_session_folder(self) -> Path:
        """Create a new timestamped session folder under scans/."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.base_dir / f"session_{timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def new_session(self) -> Path:
        """Initialize a new scanning session in a fresh timestamped directory."""
        self.pages.clear()
        self._capture_history.clear()
        self._spread_index = 0
        self.current_session_dir = self._create_session_folder()
        return self.current_session_dir

    def record_capture_batch(self, count: int) -> None:
        """Record how many pages were added in the most recent capture action."""
        if count > 0:
            self._capture_history.append(count)

    def add_page(
        self,
        image: np.ndarray,
        prefix: str = "page",
        filename: Optional[str] = None,
    ) -> ScannedPage:
        """Save captured 4K image with sequential filename and generate thumbnail.
        
        Preserves original resolution without lossy compression.
        """
        page_index = len(self.pages) + 1
        if not filename:
            filename = f"{prefix}_{page_index:03d}.png"
        file_path = self.current_session_dir / filename

        # Ensure no accidental filename collision
        collision_counter = 1
        while file_path.exists():
            stem = Path(filename).stem
            ext = Path(filename).suffix or ".png"
            file_path = self.current_session_dir / f"{stem}_{collision_counter}{ext}"
            collision_counter += 1

        # Write original lossless PNG
        cv2.imwrite(str(file_path), image)

        # Generate lightweight thumbnail for gallery UI
        thumb_filename = f"thumb_{file_path.stem}.jpg"
        thumb_path = self.current_session_dir / thumb_filename
        h, w = image.shape[:2]
        thumb_h = 240
        thumb_w = max(1, int(w * (thumb_h / float(h))))
        thumbnail = cv2.resize(image, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(thumb_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])

        page = ScannedPage(
            id=f"{file_path.stem}",
            file_path=file_path,
            page_number=page_index,
            width=w,
            height=h,
            thumbnail_path=thumb_path,
        )
        self.pages.append(page)
        return page

    def add_capture_results(self, results: list) -> List[ScannedPage]:
        """Add pages from a capture batch (single page or dual-page spread).
        
        Naming convention:
            - Dual page spread: Page_001_L.png, Page_001_R.png, Page_002_L.png, etc.
            - Single page: Page_001.png, Page_002.png, etc.
        """
        self._spread_index += 1
        added = []
        if len(results) == 2:
            left_name = f"Page_{self._spread_index:03d}_L.png"
            right_name = f"Page_{self._spread_index:03d}_R.png"
            p1 = self.add_page(results[0], filename=left_name)
            p2 = self.add_page(results[1], filename=right_name)
            added.extend([p1, p2])
        else:
            for img in results:
                name = f"Page_{self._spread_index:03d}.png"
                added.append(self.add_page(img, filename=name))
        self.record_capture_batch(len(added))
        return added

    def undo_last_capture(self) -> List[ScannedPage]:
        """Undo the most recent capture batch, removing its pages and deleting files from disk."""
        if not self.pages:
            return []

        # Number of pages to undo is determined by the last capture batch (1 or 2), defaulting to 1
        count = self._capture_history.pop() if self._capture_history else 1
        count = min(count, len(self.pages))

        removed_pages = []
        for _ in range(count):
            page = self.pages.pop()
            self._delete_page_files(page)
            removed_pages.append(page)

        self._spread_index = max(0, self._spread_index - 1)

        # Re-index remaining pages
        for idx, p in enumerate(self.pages):
            p.page_number = idx + 1

        return removed_pages

    def remove_page(self, index: int, delete_files: bool = True) -> Optional[ScannedPage]:
        """Remove a single page from session by index and delete files if requested."""
        if 0 <= index < len(self.pages):
            page = self.pages.pop(index)
            if delete_files:
                self._delete_page_files(page)
            # Reindex remaining pages
            for idx, p in enumerate(self.pages):
                p.page_number = idx + 1
            return page
        return None

    def _delete_page_files(self, page: ScannedPage) -> None:
        """Safely delete image and thumbnail files from disk."""
        try:
            if page.file_path and page.file_path.exists():
                page.file_path.unlink()
        except OSError:
            pass

        try:
            if page.thumbnail_path and page.thumbnail_path.exists():
                page.thumbnail_path.unlink()
        except OSError:
            pass

    def get_pages(self) -> List[ScannedPage]:
        """Return all scanned pages in current order."""
        return list(self.pages)

    def reorder_pages(self, new_order: List[int]) -> None:
        """Reorder pages according to list of indices."""
        self.pages = [self.pages[i] for i in new_order if 0 <= i < len(self.pages)]
        for idx, page in enumerate(self.pages):
            page.page_number = idx + 1

    def get_default_pdf_path(self) -> Path:
        """Return path for output.pdf inside the current session folder."""
        return self.current_session_dir / "output.pdf"

    def clear(self) -> None:
        """Clear all active session pages and start a fresh session folder."""
        self.new_session()
