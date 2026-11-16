"""Background camera worker thread for non-blocking video streaming."""
import time
from typing import Optional
import numpy as np
from PySide6.QtCore import QThread, Signal

from camera import BaseCamera


class CameraWorker(QThread):
    """Acquires live camera frames continuously in a dedicated QThread."""

    frame_ready = Signal(np.ndarray)
    fps_updated = Signal(float)
    error_occurred = Signal(str)
    connection_changed = Signal(bool)

    def __init__(self, camera: BaseCamera, parent=None):
        super().__init__(parent)
        self.camera = camera
        self._running = False
        self._target_fps = 30.0

    def run(self) -> None:
        """Main thread loop for frame acquisition."""
        if not self.camera.open():
            self.error_occurred.emit("Unable to open camera stream.")
            self.connection_changed.emit(False)
            return

        self._running = True
        self.connection_changed.emit(True)

        frame_count = 0
        consecutive_failures = 0
        start_time = time.time()
        frame_delay = 1.0 / self._target_fps

        try:
            while self._running:
                loop_start = time.time()

                ret, frame = self.camera.read_frame()
                if not self._running:
                    break

                if ret and frame is not None:
                    self.frame_ready.emit(frame)
                    frame_count += 1
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= 60:  # ~2 seconds of no frames
                        self.error_occurred.emit("Camera disconnected or stopped sending frames.")
                        break
                    time.sleep(0.01)

                # Compute actual rolling FPS every 30 frames
                if frame_count >= 30:
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        fps = frame_count / elapsed
                        self.fps_updated.emit(fps)
                    frame_count = 0
                    start_time = time.time()

                # Throttle preview acquisition to keep CPU cool while maintaining responsive UI
                elapsed_loop = time.time() - loop_start
                sleep_time = max(0.001, frame_delay - elapsed_loop)
                time.sleep(sleep_time)
        finally:
            self.camera.close()
            if self._running:
                self._running = False
                self.connection_changed.emit(False)

    def stop(self) -> None:
        """Signal thread to stop and wait for cleanup."""
        self._running = False
        if not self.wait(2000):
            # If thread didn't exit in 2 seconds, terminate
            self.terminate()
            self.wait(500)

