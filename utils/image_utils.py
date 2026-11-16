"""Image and vision utility functions."""
from typing import Optional, Tuple
import numpy as np
from PySide6.QtGui import QImage, QPixmap


def cv_mat_to_qimage(mat: np.ndarray) -> QImage:
    """Convert an OpenCV BGR or Grayscale matrix to QImage without losing bit depth."""
    if mat is None:
        return QImage()

    if len(mat.shape) == 2:
        # Grayscale image
        height, width = mat.shape
        bytes_per_line = width
        return QImage(
            mat.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8
        ).copy()
    elif len(mat.shape) == 3:
        height, width, channels = mat.shape
        if channels == 3:
            # OpenCV stores BGR; convert representation directly for QImage RGB888
            bytes_per_line = channels * width
            # Format_BGR888 is natively supported in PySide6 / Qt6
            return QImage(
                mat.data, width, height, bytes_per_line, QImage.Format.Format_BGR888
            ).copy()
        elif channels == 4:
            bytes_per_line = channels * width
            return QImage(
                mat.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888
            ).copy()

    return QImage()


def cv_mat_to_qpixmap(mat: np.ndarray) -> QPixmap:
    """Convert an OpenCV BGR image directly to QPixmap."""
    qimg = cv_mat_to_qimage(mat)
    if qimg.isNull():
        return QPixmap()
    return QPixmap.fromImage(qimg)


def scale_preview(
    mat: np.ndarray, target_size: Tuple[int, int]
) -> np.ndarray:
    """Safely calculate scaled preview maintaining aspect ratio.
    
    Original 4K captures must NEVER be passed to this function for storage.
    This is strictly for real-time UI display optimization.
    """
    import cv2

    target_w, target_h = target_size
    if target_w <= 0 or target_h <= 0 or mat is None:
        return mat

    h, w = mat.shape[:2]
    aspect = w / float(h)
    target_aspect = target_w / float(target_h)

    if aspect > target_aspect:
        new_w = target_w
        new_h = int(new_w / aspect)
    else:
        new_h = target_h
        new_w = int(new_h * aspect)

    return cv2.resize(mat, (max(1, new_w), max(1, new_h)), interpolation=cv2.INTER_AREA)

