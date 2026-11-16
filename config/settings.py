"""Application configuration and settings."""
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent.parent
SCANS_DIR = BASE_DIR / "scans"
TEST_IMAGES_DIR = BASE_DIR / "test_images"

# Ensure runtime directories exist
SCANS_DIR.mkdir(parents=True, exist_ok=True)
TEST_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CameraConfig:
    """Camera acquisition configurations."""
    default_width: int = 3840  # 4K UHD
    default_height: int = 2160
    default_fps: int = 30
    preview_fps: int = 30
    backend_preference: str = "DSHOW"  # DirectShow on Windows


@dataclass
class ProcessingConfig:
    """Image processing and page enhancement defaults."""
    enable_auto_detect: bool = True
    split_dual_pages: bool = True
    output_dpi: int = 300
    color_mode: str = "Color"  # "Color", "Grayscale", "B&W Enhanced"

