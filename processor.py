"""Computer vision document processing algorithms."""
from typing import List, Optional, Tuple
import cv2
import numpy as np


class DocumentProcessor:
    """Handles page boundary detection, perspective correction, splitting, and enhancement."""

    @staticmethod
    def detect_page_boundary(image: np.ndarray) -> Optional[np.ndarray]:
        """Detect four corners of the largest bright document quadrilateral against a dark background.
        
        Handles uneven lighting via adaptive morphological binarization combined with edge contours.

        Returns:
            np.ndarray of shape (4, 2) with coordinates [TL, TR, BR, BL] in original image space, or None.
        """
        if image is None or image.size == 0:
            return None

        # Work on a scaled down proxy for fast detection
        h, w = image.shape[:2]
        scale = 800.0 / max(h, w)
        small = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 1. Edge-based detection with morphological closing (works for both dark and bright objects)
        edges = cv2.Canny(blurred, 30, 120)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        # 2. Lighting-tolerant Otsu thresholding for bright document vs dark desk
        _, otsu_mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        otsu_closed = cv2.morphologyEx(otsu_mask, cv2.MORPH_CLOSE, kernel)

        # 3. Combined mask for low-contrast edges
        combined_mask = cv2.bitwise_or(closed_edges, otsu_closed)

        img_area = float(small.shape[0] * small.shape[1])
        frame_center = np.array([small.shape[1] / 2.0, small.shape[0] / 2.0])

        candidates = []

        # Probe candidate masks: edge-first (catches dark objects/phones & books), then Otsu & combined
        for mask in (closed_edges, otsu_closed, combined_mask):
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue

            for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
                area = cv2.contourArea(contour)
                if area < (img_area * 0.08) or area > (img_area * 0.95):
                    continue

                hull = cv2.convexHull(contour)
                peri = cv2.arcLength(hull, True)

                # Try varying tolerances to find 4-corner polygon
                for eps_factor in (0.02, 0.03, 0.04, 0.015, 0.05):
                    approx = cv2.approxPolyDP(hull, eps_factor * peri, True)
                    if len(approx) == 4 and cv2.isContourConvex(approx):
                        pts = approx.reshape(4, 2)
                        ordered = DocumentProcessor.order_points(pts)
                        if DocumentProcessor._validate_quadrilateral(ordered):
                            # Score: prioritize centrality and reasonable area
                            poly_center = ordered.mean(axis=0)
                            dist_from_center = np.linalg.norm(poly_center - frame_center)
                            # Closer to center + good area gets higher score
                            score = area - (dist_from_center * 15.0)
                            candidates.append((score, ordered / scale))
                            break

        if candidates:
            # Return candidate with best score
            candidates.sort(key=lambda c: c[0], reverse=True)
            return candidates[0][1]

        return None

    @staticmethod
    def _validate_quadrilateral(pts: np.ndarray) -> bool:
        """Verify quadrilateral points form a non-degenerate shape with positive area."""
        if pts is None or pts.shape != (4, 2):
            return False
        # Calculate polygon area via Shoelace formula
        x = pts[:, 0]
        y = pts[:, 1]
        area = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        return area > 100.0

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """Order coordinates consistently: [top-left, top-right, bottom-right, bottom-left]."""
        pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
        rect = np.zeros((4, 2), dtype=np.float32)

        # Top-left has smallest sum (x + y), bottom-right has largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # Top-right has smallest difference (y - x), bottom-left has largest diff
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    @staticmethod
    def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """Apply perspective warp on high-resolution image using corner points.
        
        Preserves original resolution and fine detail using INTER_CUBIC interpolation.
        """
        if image is None or image.size == 0:
            return image

        if pts is None or not DocumentProcessor._validate_quadrilateral(pts):
            return image.copy()

        rect = DocumentProcessor.order_points(pts)
        (tl, tr, br, bl) = rect

        # Compute width of new image
        width_a = np.hypot(br[0] - bl[0], br[1] - bl[1])
        width_b = np.hypot(tr[0] - tl[0], tr[1] - tl[1])
        max_width = max(int(width_a), int(width_b))

        # Compute height of new image
        height_a = np.hypot(tr[0] - br[0], tr[1] - br[1])
        height_b = np.hypot(tl[0] - bl[0], tl[1] - bl[1])
        max_height = max(int(height_a), int(height_b))

        if max_width < 10 or max_height < 10:
            return image.copy()

        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ], dtype=np.float32)

        try:
            transform_matrix = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(
                image,
                transform_matrix,
                (max_width, max_height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return warped
        except cv2.error:
            return image.copy()

    @staticmethod
    def split_spread(
        image: np.ndarray, spine_ratio: float = 0.5, spine_margin_ratio: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Split a dual-page spread image into left and right individual pages.
        
        Args:
            image: Perspective-corrected spread image.
            spine_ratio: Normalized horizontal position of center spine (0.2 to 0.8).
            spine_margin_ratio: Optional overlap margin ratio (default 0.0).

        Returns:
            Tuple of (left_page, right_page).
        """
        h, w = image.shape[:2]
        clamped_ratio = float(np.clip(spine_ratio, 0.2, 0.8))
        spine_x = int(w * clamped_ratio)
        margin = int(w * max(0.0, spine_margin_ratio))

        left_end = min(w, max(1, spine_x + margin))
        right_start = max(0, min(w - 1, spine_x - margin))

        left_crop = image[:, :left_end].copy()
        right_crop = image[:, right_start:].copy()

        return left_crop, right_crop

    @staticmethod
    def enhance_document(image: np.ndarray, mode: str = "Original Color") -> np.ndarray:
        """Apply document readability enhancements.
        
        Modes:
            1. "Original Color": Unmodified captured & perspective-corrected image.
            2. "Enhanced Document Color": White balance correction and CLAHE on luminance,
               preserving stamps and blue/red handwriting ink.
            3. "Clean Black & White": Adaptive Gaussian thresholding for high text legibility.
            4. "Grayscale": Contrast-limited adaptive histogram equalization in grayscale.
        """
        if image is None or image.size == 0:
            return image

        mode_clean = mode.strip().lower()

        # 1. Original Color: pure unmodified copy
        if "original" in mode_clean or mode_clean == "color":
            return image.copy()

        # 2. Enhanced Document Color: white balance correction + CLAHE luminance
        elif "enhanced" in mode_clean and "color" in mode_clean:
            # White balance correction via percentile balancing
            balanced = np.zeros_like(image)
            for ch_idx in range(3):
                ch = image[:, :, ch_idx]
                p_low, p_high = np.percentile(ch, (1.0, 99.0))
                if p_high > p_low:
                    scaled = np.clip(
                        (ch.astype(np.float32) - p_low) * (255.0 / (p_high - p_low)),
                        0,
                        255,
                    ).astype(np.uint8)
                    balanced[:, :, ch_idx] = scaled
                else:
                    balanced[:, :, ch_idx] = ch

            # Convert to LAB to equalize luminance only (preserving colors/stamps)
            lab = cv2.cvtColor(balanced, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced_lab = cv2.merge((l, a, b))
            return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # 3. Clean Black & White: Adaptive Gaussian thresholding
        elif "black" in mode_clean or "b&w" in mode_clean:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Bilateral filter to smooth paper background without blurring text edges
            denoised = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)
            binary = cv2.adaptiveThreshold(
                denoised,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=21,
                C=10,
            )
            return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

        # 4. Grayscale (Optional)
        elif "gray" in mode_clean:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

        # Default fallback
        return image.copy()
