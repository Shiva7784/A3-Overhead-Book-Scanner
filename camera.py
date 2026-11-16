"""Camera interface and hardware UVC controller."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CameraCapability:
    """Represents actual hardware capability."""
    width: int
    height: int
    fps: float
    backend: str


@dataclass
class UvcControl:
    """Represents a hardware camera property."""
    prop_id: int
    name: str
    min_val: float
    max_val: float
    step: float
    default_val: float
    current_val: float
    is_supported: bool


class BaseCamera(ABC):
    """Abstract base camera class."""

    @abstractmethod
    def open(self) -> bool:
        """Open camera stream."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close camera stream and release resources."""
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """Check if camera stream is active."""
        pass

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read current live preview frame (BGR)."""
        pass

    @abstractmethod
    def capture_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Capture full-resolution frame (up to 4K)."""
        pass

    @abstractmethod
    def get_capabilities(self) -> Optional[CameraCapability]:
        """Query actual verified camera capabilities."""
        pass

    @abstractmethod
    def get_controls(self) -> Dict[str, UvcControl]:
        """Query supported UVC hardware controls."""
        pass

    @abstractmethod
    def set_control(self, name: str, value: float) -> bool:
        """Set a specific UVC property value."""
        pass

    def reset_controls(self) -> Dict[str, float]:
        """Reset controls to calibrated hardware defaults."""
        return {}


class PhysicalUvcCamera(BaseCamera):
    """Hardware UVC camera implementation via OpenCV DirectShow / MSMF."""

    # Common UVC properties mapped to OpenCV
    UVC_PROPERTIES: Dict[str, int] = {
        "exposure": cv2.CAP_PROP_EXPOSURE,
        "auto_exposure": cv2.CAP_PROP_AUTO_EXPOSURE,
        "focus": cv2.CAP_PROP_FOCUS,
        "autofocus": cv2.CAP_PROP_AUTOFOCUS,
        "brightness": cv2.CAP_PROP_BRIGHTNESS,
        "contrast": cv2.CAP_PROP_CONTRAST,
        "saturation": cv2.CAP_PROP_SATURATION,
        "white_balance": getattr(cv2, "CAP_PROP_WB_TEMPERATURE", 45),
        "auto_wb": getattr(cv2, "CAP_PROP_AUTO_WB", 44),
        "zoom": getattr(cv2, "CAP_PROP_ZOOM", 27),
    }

    def __init__(
        self,
        device_index: int = 0,
        target_width: int = 3840,
        target_height: int = 2160,
        preferred_fps: int = 30,
    ):
        self.device_index = device_index
        self.target_width = target_width
        self.target_height = target_height
        self.preferred_fps = preferred_fps
        self.cap: Optional[cv2.VideoCapture] = None
        self._capabilities: Optional[CameraCapability] = None
        self._controls: Dict[str, UvcControl] = {}

    def open(self) -> bool:
        try:
            if self.cap is not None:
                self.close()

            # Prefer DirectShow on Windows for fast 4K UVC negotiation
            backend = cv2.CAP_DSHOW
            self.cap = cv2.VideoCapture(self.device_index, backend)
            if not self.cap.isOpened():
                # Fallback to default backend
                self.cap = cv2.VideoCapture(self.device_index)

            if not self.cap.isOpened():
                logger.error(f"Failed to open camera index {self.device_index}")
                return False

            # Force MJPG FOURCC to ensure high-bandwidth 4K UVC streaming
            try:
                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
            except Exception as e:
                logger.warning(f"Could not force MJPG FOURCC: {e}")

            # Request target resolution (default 3840 x 2160)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.preferred_fps)

            # Warmup: flush a few initial frames
            for _ in range(3):
                self.cap.read()

            # Verify actual resolution negotiated by hardware
            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = float(self.cap.get(cv2.CAP_PROP_FPS))
            backend_name = self.cap.getBackendName()

            self._capabilities = CameraCapability(
                width=actual_w if actual_w > 0 else self.target_width,
                height=actual_h if actual_h > 0 else self.target_height,
                fps=actual_fps if actual_fps > 0 else self.preferred_fps,
                backend=backend_name,
            )
            logger.info(f"Connected to camera {self.device_index}: {actual_w}x{actual_h} @ {actual_fps}fps ({backend_name})")

            self._query_supported_controls()
            return True
        except Exception as e:
            logger.exception(f"Error opening camera: {e}")
            self.close()
            return False

    def _query_supported_controls(self) -> None:
        """Probe available UVC hardware controls."""
        if not self.cap or not self.cap.isOpened():
            return

        self._controls.clear()
        for name, prop_id in self.UVC_PROPERTIES.items():
            try:
                curr_val = self.cap.get(prop_id)
                # Test if the hardware responded with a valid non-error code
                is_supported = curr_val != -1 and not np.isnan(curr_val)
                self._controls[name] = UvcControl(
                    prop_id=prop_id,
                    name=name,
                    min_val=-10.0,
                    max_val=10.0,
                    step=1.0,
                    default_val=curr_val if is_supported else 0.0,
                    current_val=curr_val if is_supported else 0.0,
                    is_supported=is_supported,
                )
            except Exception:
                pass

    def close(self) -> None:
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception as e:
                logger.warning(f"Error releasing camera: {e}")
            finally:
                self.cap = None
                self._capabilities = None
                self._controls.clear()
            # Brief pause to ensure OS driver releases device handle cleanly
            import time
            time.sleep(0.08)

    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.is_opened() or self.cap is None:
            return False, None
        ret, frame = self.cap.read()
        return ret, frame

    def capture_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Grab high-resolution unscaled 4K frame directly from buffer."""
        if not self.is_opened() or self.cap is None:
            return False, None
        # Flush buffer to ensure latest instant capture
        for _ in range(2):
            self.cap.grab()
        ret, frame = self.cap.retrieve()
        return ret, frame

    def get_capabilities(self) -> Optional[CameraCapability]:
        return self._capabilities

    def get_controls(self) -> Dict[str, UvcControl]:
        return self._controls

    def set_control(self, name: str, value: float) -> bool:
        if not self.is_opened() or self.cap is None:
            return False
        if name == "auto_exposure":
            # In DirectShow: 0.75 is Auto, 0.25 is Manual
            val_to_set = 0.75 if value > 0.5 else 0.25
            success = self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, val_to_set)
            if success and "auto_exposure" in self._controls:
                self._controls["auto_exposure"].current_val = 1.0 if value > 0.5 else 0.0
            return bool(success)
        elif name == "autofocus":
            val_to_set = 1.0 if value > 0.5 else 0.0
            success = self.cap.set(cv2.CAP_PROP_AUTOFOCUS, val_to_set)
            if success and "autofocus" in self._controls:
                self._controls["autofocus"].current_val = val_to_set
            return bool(success)
        elif name in self.UVC_PROPERTIES:
            prop_id = self.UVC_PROPERTIES[name]
            success = self.cap.set(prop_id, value)
            if success and name in self._controls:
                self._controls[name].current_val = value
            return bool(success)
        return False

    def reset_controls(self) -> Dict[str, float]:
        """Reset hardware controls to camera manufacturer recommended defaults."""
        # Set color and picture controls first
        self.set_control("brightness", 0.0)
        self.set_control("contrast", 50.0)
        self.set_control("saturation", 64.0)
        self.set_control("autofocus", 1.0)

        # Set Auto Exposure mode last (do NOT set manual exposure, as that overrides auto mode in DirectShow)
        self.set_control("auto_exposure", 1.0)

        return {
            "brightness": 0.0,
            "contrast": 50.0,
            "saturation": 64.0,
            "exposure": -6.0,
            "auto_exposure": 1.0,
            "autofocus": 1.0,
        }


class NetworkStreamCamera(BaseCamera):
    """Network IP camera or phone stream (HTTP / RTSP / MJPEG)."""

    def __init__(self, stream_url: str):
        self.stream_url = stream_url.strip()
        self.cap: Optional[cv2.VideoCapture] = None
        self._capabilities: Optional[CameraCapability] = None
        self._controls: Dict[str, UvcControl] = {}

    def open(self) -> bool:
        try:
            if self.cap is not None:
                self.close()

            self.cap = cv2.VideoCapture(self.stream_url)
            if not self.cap.isOpened():
                logger.error(f"Failed to connect to IP camera at {self.stream_url}")
                return False

            # Verify actual resolution delivered by stream
            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = float(self.cap.get(cv2.CAP_PROP_FPS))
            backend_name = self.cap.getBackendName()

            self._capabilities = CameraCapability(
                width=actual_w if actual_w > 0 else 1920,
                height=actual_h if actual_h > 0 else 1080,
                fps=actual_fps if actual_fps > 0 else 30.0,
                backend=f"IPStream ({backend_name})",
            )
            logger.info(f"Connected to IP camera {self.stream_url}: {actual_w}x{actual_h}")
            return True
        except Exception as e:
            logger.exception(f"Error opening IP stream: {e}")
            self.close()
            return False

    def close(self) -> None:
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception as e:
                logger.warning(f"Error releasing IP stream: {e}")
            finally:
                self.cap = None
                self._capabilities = None

    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.is_opened() or self.cap is None:
            return False, None
        return self.cap.read()

    def capture_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.is_opened() or self.cap is None:
            return False, None
        for _ in range(2):
            self.cap.grab()
        return self.cap.retrieve()

    def get_capabilities(self) -> Optional[CameraCapability]:
        return self._capabilities

    def get_controls(self) -> Dict[str, UvcControl]:
        return self._controls

    def set_control(self, name: str, value: float) -> bool:
        return True


class MockFolderCamera(BaseCamera):
    """Simulated camera mode loading images from a designated folder or generating test pattern."""

    def __init__(self, folder_path: Path, width: int = 3840, height: int = 2160):
        self.folder_path = folder_path
        self.width = width
        self.height = height
        self._is_opened = False
        self._image_files: List[Path] = []
        self._current_index = 0
        self._controls: Dict[str, UvcControl] = {}
        self._simulated_frame: Optional[np.ndarray] = None

    def open(self) -> bool:
        self.folder_path.mkdir(parents=True, exist_ok=True)
        valid_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
        self._image_files = [
            f for f in self.folder_path.iterdir() if f.suffix.lower() in valid_extensions
        ]
        self._image_files.sort()

        if not self._image_files:
            # Generate a realistic A3 dual-page book mock frame
            self._simulated_frame = self._generate_mock_a3_book()
        else:
            self._simulated_frame = None

        self._is_opened = True
        return True

    def _generate_mock_a3_book(self) -> np.ndarray:
        """Create a synthetic high-resolution 4K A3 book spread with border, spine, and text lines."""
        # 4K canvas (3840 x 2160)
        img = np.full((self.height, self.width, 3), 45, dtype=np.uint8)  # Dark desktop background

        # Book spread bounding box (perspective simulated)
        margin_x = int(self.width * 0.10)
        margin_y = int(self.height * 0.10)
        book_w = self.width - 2 * margin_x
        book_h = self.height - 2 * margin_y

        # Draw off-white book spread
        cv2.rectangle(
            img,
            (margin_x, margin_y),
            (margin_x + book_w, margin_y + book_h),
            (240, 242, 245),
            thickness=-1,
        )

        # Draw book spine shadow
        spine_x = margin_x + book_w // 2
        cv2.line(img, (spine_x, margin_y), (spine_x, margin_y + book_h), (160, 160, 165), 8)
        cv2.line(img, (spine_x - 10, margin_y), (spine_x - 10, margin_y + book_h), (210, 210, 215), 12)
        cv2.line(img, (spine_x + 10, margin_y), (spine_x + 10, margin_y + book_h), (210, 210, 215), 12)

        # Draw left page header & simulated service register columns
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, "SERVICE REGISTER - LEFT PAGE (A3 SPREAD)", (margin_x + 80, margin_y + 120), font, 1.8, (20, 20, 20), 4)
        cv2.putText(img, "SERVICE REGISTER - RIGHT PAGE (A3 SPREAD)", (spine_x + 80, margin_y + 120), font, 1.8, (20, 20, 20), 4)

        # Draw sample table rows on both pages
        for row_y in range(margin_y + 200, margin_y + book_h - 100, 120):
            # Left page rows
            cv2.line(img, (margin_x + 60, row_y), (spine_x - 60, row_y), (180, 180, 180), 2)
            cv2.putText(img, f"Log Entry #{int(row_y/10)} | Description & Equipment Check", (margin_x + 80, row_y - 20), font, 1.1, (60, 60, 60), 2)
            # Right page rows
            cv2.line(img, (spine_x + 60, row_y), (margin_x + book_w - 60, row_y), (180, 180, 180), 2)
            cv2.putText(img, f"Status: COMPLIANT | Verified By: Tech #{int(row_y/20)}", (spine_x + 80, row_y - 20), font, 1.1, (60, 60, 60), 2)

        return img

    def close(self) -> None:
        self._is_opened = False

    def is_opened(self) -> bool:
        return self._is_opened

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self._is_opened:
            return False, None

        if self._image_files:
            file_to_load = self._image_files[self._current_index % len(self._image_files)]
            mat = cv2.imread(str(file_to_load))
            return (mat is not None), mat
        elif self._simulated_frame is not None:
            # Return copy of simulated high-res frame
            return True, self._simulated_frame.copy()

        return False, None

    def capture_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        ret, frame = self.read_frame()
        if ret and self._image_files:
            # Advance to next image on capture in mock folder mode
            self._current_index = (self._current_index + 1) % len(self._image_files)
        return ret, frame

    def get_capabilities(self) -> Optional[CameraCapability]:
        return CameraCapability(
            width=self.width,
            height=self.height,
            fps=30.0,
            backend="MockFolderMode",
        )

    def get_controls(self) -> Dict[str, UvcControl]:
        return self._controls

    def set_control(self, name: str, value: float) -> bool:
        return True
