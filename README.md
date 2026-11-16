# A3 Overhead Book Scanner – Professional Production Edition

A high-performance desktop application built with **Python 3.12**, **PySide6 (Qt6)**, and **OpenCV** designed to digitize large physical service registers, bound ledgers, and A3 books using an overhead-mounted UVC-compliant 4K USB camera.

---

## 🌟 Key Features

- **Direct 4K UHD UVC Negotiation**: Negotiates up to 3840×2160 resolution forcing `MJPG` FOURCC for high USB bandwidth. Reads back and displays verified hardware resolution and framerate.
- **Asynchronous Non-Blocking Pipeline**: Decoupled `QThread` streaming and worker threads keep preview streaming at responsive framerates while heavy 4K perspective transformations, enhancement filters, and PDF packaging run without freezing the UI.
- **Lighting-Tolerant Boundary Detection**: Dual edge and adaptive binarization algorithms detect book pages under uneven ambient illumination.
- **Interactive 4-Corner Perspective Adjustment**: Four draggable corner grab-handles (`TL`, `TR`, `BL`, `BR`) with a green overlay polygon allow precise manual alignment mapped directly to original full-resolution coordinates.
- **Dual-Page Spread Splitting**: Splits A3 spreads into sequential `Page_001_L.png` and `Page_001_R.png` pages with a live-preview center-line spine offset slider.
- **Three Core Enhancement Modes**:
  1. **Original Color**: Completely unmodified captured and perspective-corrected frame.
  2. **Enhanced Document Color**: Percentile white-balance leveling + CLAHE on luminance, preserving colored stamps and blue/red ink.
  3. **Clean Black & White**: Bilateral edge-preserving denoising + adaptive Gaussian thresholding for high text legibility.
- **Interactive Fullscreen Page Viewer**: Modal lightbox viewer with mouse-wheel zoom (10% to 500%), click-and-drag panning, fit-to-window, and full-resolution inspection.
- **Lossless Multi-Page PDF Generation**: Directly packages full-resolution scanned pages at 300 DPI using `img2pdf` without re-compression into `output.pdf`.
- **Timestamped Session Management**: Automatically isolates scans in timestamped session folders (`scans/session_YYYYMMDD_HHMMSS/`) with batch undo support (Shortcut `Z`).

---

## 🏛 Application Architecture

```
python projects/
├── main.py                     # Application entry point, CLI arguments, and lifecycle
├── camera.py                   # Hardware UVC camera abstraction, DirectShow & mock cameras
├── processor.py                # Computer vision pipeline (detection, perspective warp, split, enhancement)
├── pdf_exporter.py             # Multi-page lossless PDF compiler using img2pdf
├── requirements.txt            # Python package dependencies
├── README.md                   # Comprehensive documentation & engineering guide
│
├── config/
│   └── settings.py             # Default paths, target resolutions, and directories
├── services/
│   └── session_manager.py      # Session folder creation, page ordering, batch undo & disk persistence
├── workers/
│   ├── camera_worker.py        # QThread worker for live camera acquisition and FPS calculation
│   └── processing_worker.py    # QThread worker for 4K warp, enhancement, splitting, and PDF export
├── utils/
│   └── image_utils.py          # Format conversions (OpenCV BGR <-> QImage/QPixmap)
├── ui/
│   ├── main_window.py          # Main application window, splitters, status bar, and shortcuts
│   ├── camera_panel.py         # Left panel: Device selector, refresh, resolution, UVC controls
│   ├── preview_panel.py        # Central viewport: Live feed canvas with green interactive polygon
│   ├── processing_panel.py     # Right panel: Boundary detection, split settings, enhancement presets
│   ├── gallery_panel.py        # Bottom panel: Thumbnail gallery, page reordering, full viewer trigger
│   ├── page_viewer_dialog.py   # Modal high-resolution fullscreen image viewer with zoom & pan
│   └── styles.py               # Professional dark theme stylesheet (QSS)
├── tests/
│   ├── test_processor.py       # CV unit tests (warp, boundary detection, split, enhancements)
│   ├── test_session.py         # Session management, sequential naming, undo, and file deletion tests
│   └── test_pdf.py             # Multi-page PDF generation tests
├── test_images/                # Sample test images for mock development mode
└── scans/                      # Session scan output directories and generated PDF documents
```

---

## ⚙️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.9+ (Verified on 3.12) | Core language |
| **Desktop UI** | PySide6 (Qt 6.5+) | Native responsive desktop GUI & dark theme |
| **Computer Vision** | OpenCV (`opencv-python`) | DirectShow UVC capture, MJPG pin, Canny/Otsu, perspective transform |
| **Array Computing** | NumPy | High-performance coordinate mapping and color space manipulation |
| **Image Encoding** | Pillow (PIL) | Image verification and thumbnail rendering |
| **PDF Generation** | `img2pdf` | Lossless stream-level image packaging into PDF containers |
| **DirectShow Probing** | `pygrabber` | Windows DirectShow video capture device enumeration |
| **Testing** | `pytest` | Automated unit and integration test suite |

---

## 🚀 Installation & Setup

### 1. Prerequisites
Ensure Python 3.9 or higher is installed on Windows:
```powershell
python --version
```

### 2. Install Dependencies
Install all required libraries from `requirements.txt`:
```powershell
pip install -r requirements.txt
```

### 3. Running the Application

#### Standard Mode (Overhead Physical Camera)
```powershell
python main.py
```
1. Select **Physical UVC 4K Camera** as the source mode.
2. Select your overhead camera from the **Device** dropdown (click **`🔄 Refresh`** if plugged in after launch).
3. Select **3840 x 2160 (4K UHD)** as target resolution.
4. Click **Connect**.

#### Mock Development Mode (Simulated 4K A3 Register)
```powershell
python main.py --mock
```
*In mock mode, the application generates a synthetic 4K A3 double-page service register with table columns, handwriting, text lines, and spine shadow, allowing full testing of detection, warping, page splitting, enhancement, and PDF export without needing a physical camera.*

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action | Description |
|---|---|---|
| **Space** / **Enter** | **Capture Spread** | Grabs uncompressed 4K frame, warps, enhances, and saves pages. |
| **Z** | **Undo Capture** | Removes the last captured page batch and deletes its files from disk. |
| **S** | **Toggle Page Mode** | Toggles between Dual-Page mode (A3 -> 2x A4) and Single-Page mode. |
| **M** | **Cycle Enhancement** | Cycles through Original Color → Enhanced Document Color → Clean B&W. |
| **P** | **Export PDF** | Compiles all session pages into a lossless multi-page PDF. |
| **F** *(Viewer)* | **Fullscreen** | Toggles fullscreen mode when inspecting a captured page. |
| **Esc** *(Viewer)* | **Close Viewer** | Closes the high-resolution page preview lightbox. |

*Note: All single-key shortcuts automatically yield focus when typing in text fields (e.g. phone stream URL).*

---

## 🎨 Supported Enhancement Modes

1. **Original Color**:
   * Completely unmodified perspective-corrected capture. Preserves exact natural color tone and sensor fidelity.
2. **Enhanced Document Color**:
   * Percentile-based white balance leveling removes paper yellowing and ambient warm cast.
   * Contrast-Limited Adaptive Histogram Equalization (CLAHE) is applied strictly to the luminance (`L`) channel in LAB color space, preserving red ink, blue signatures, and colored official rubber stamps.
3. **Clean Black & White**:
   * Bilateral edge-preserving filtering removes paper texture and grain.
   * Adaptive Gaussian thresholding produces crisp, high-contrast monochrome text for archiving.
4. **Grayscale (Optional)**:
   * Contrast-enhanced grayscale reproduction.

---

## 📄 File Naming & Organization

Scans are stored inside timestamped folders under `scans/`:
```
scans/
└── session_20261116_160130/
    ├── Page_001_L.png         # Left page of spread 1 (lossless PNG)
    ├── Page_001_R.png         # Right page of spread 1 (lossless PNG)
    ├── Page_002_L.png         # Left page of spread 2
    ├── Page_002_R.png         # Right page of spread 2
    ├── thumb_Page_001_L.jpg   # Lightweight UI thumbnail
    ├── thumb_Page_001_R.jpg   # Lightweight UI thumbnail
    └── output.pdf             # Lossless 300 DPI multi-page PDF compilation
```

---

## 🔍 Known Hardware Limitations

1. **Physical 4K Resolution Availability**:
   * A camera will only capture at 3840×2160 if the physical sensor supports 4K. Built-in laptop webcams (e.g. `HP TrueVision HD`) negotiate at their maximum hardware ceiling (typically 1280×720 or 1920×1080).
2. **Fixed-Focus Webcams**:
   * Built-in laptop webcams lack motorized focus actuators; manual focus and autofocus sliders are automatically disabled for unsupported devices.
3. **Curved Spine Dewarping**:
   * The application uses planar 4-point perspective transformation. Physical books with steep 3D spine curvature should be held flat with a transparent glass plate.

---

## 🛠 Troubleshooting

* **Blank Preview Screen After Reset**:
  * Always use the **`↺ Reset Controls to Defaults`** button. It restores calibrated values (Contrast: 50, Brightness: 0, Saturation: 64, Auto Exposure: ON) without overriding auto-exposure mode.
* **Camera Not Listed**:
  * Plug in your USB camera and click **`🔄 Refresh`** next to the Device selector. The DirectShow graph will re-enumerate all connected video devices without requiring an application restart.
* **Page Boundary Not Snapping**:
  * Ensure the document has high contrast against the desk surface (e.g. a white page on a dark table or dark scanning mat).
  * If scanning bound ledgers with fingers holding edges, click and drag the **`TL`**, **`TR`**, **`BL`**, **`BR`** corner handles directly to the corners of the page.
* **Colors Look Washed Out or Blown Out**:
  * Click **`↺ Reset Controls to Defaults`**. Avoid cranking Contrast to 100 or Brightness to maximum, which clips color channels. Use the **Color Saturation** slider to boost vibrancy naturally.

---

## 🧪 Running Automated Tests

Run the full automated test suite (18 tests):
```powershell
python -m pytest tests/ -v
```
All tests cover quadrilateral detection, 4-point perspective transformation, page splitting, document enhancement modes, session lifecycle, sequential naming, undo file deletion, and PDF generation.
