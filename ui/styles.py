"""Professional dark theme stylesheet for A3 Overhead Book Scanner."""

DARK_THEME_QSS = """
/* Global Window Styling */
QMainWindow, QDialog, QWidget {
    background-color: #18191d;
    color: #e2e8f0;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Menu Bar */
QMenuBar {
    background-color: #121316;
    color: #cbd5e1;
    border-bottom: 1px solid #27272a;
    padding: 2px;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #27272a;
    color: #ffffff;
}

QMenu {
    background-color: #1e1f24;
    color: #e2e8f0;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
}

/* Status Bar */
QStatusBar {
    background-color: #121316;
    color: #94a3b8;
    border-top: 1px solid #27272a;
    min-height: 24px;
    padding: 2px 8px;
}

/* Group Boxes / Panels */
QGroupBox {
    background-color: #1e1f24;
    border: 1px solid #2e3038;
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 14px;
    font-weight: 600;
    color: #93c5fd;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #18191d;
}

/* Push Buttons */
QPushButton {
    background-color: #272932;
    color: #f1f5f9;
    border: 1px solid #3e414e;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #333644;
    border-color: #4f5366;
}

QPushButton:pressed {
    background-color: #1c1d24;
}

QPushButton:disabled {
    background-color: #1c1d22;
    color: #64748b;
    border-color: #27272a;
}

/* Primary Action Buttons */
QPushButton#primaryActionBtn {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
    font-weight: 700;
    font-size: 14px;
    padding: 10px 18px;
}

QPushButton#primaryActionBtn:hover {
    background-color: #1d4ed8;
}

QPushButton#primaryActionBtn:pressed {
    background-color: #1e40af;
}

QPushButton#successActionBtn {
    background-color: #059669;
    color: #ffffff;
    border: 1px solid #10b981;
    font-weight: 600;
    padding: 8px 16px;
}

QPushButton#successActionBtn:hover {
    background-color: #047857;
}

/* Combo Boxes */
QComboBox {
    background-color: #272932;
    color: #f1f5f9;
    border: 1px solid #3e414e;
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 22px;
}

QComboBox:hover {
    border-color: #60a5fa;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1e1f24;
    color: #f1f5f9;
    border: 1px solid #3f3f46;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #2e3038;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #60a5fa;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #93c5fd;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #475569;
    border-radius: 4px;
    background-color: #272932;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
}

/* Progress Bar */
QProgressBar {
    background-color: #272932;
    border: 1px solid #3e414e;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    height: 14px;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 5px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #18191d;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #3e414e;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #64748b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #18191d;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #3e414e;
    border-radius: 4px;
    min-width: 20px;
}

/* List Widgets / Gallery */
QListWidget {
    background-color: #121316;
    border: 1px solid #2e3038;
    border-radius: 8px;
    padding: 6px;
}

QListWidget::item {
    border-radius: 6px;
    padding: 6px;
    margin-right: 8px;
}

QListWidget::item:selected {
    background-color: #1e3a8a;
    border: 1px solid #3b82f6;
}

/* Labels */
QLabel {
    color: #e2e8f0;
}

QLabel#panelTitle {
    font-size: 15px;
    font-weight: 700;
    color: #f8fafc;
}

QLabel#statusBadge {
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: 600;
}
"""

