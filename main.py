"""A3 Overhead Book Scanner - Application Entry Point."""
import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from ui.styles import DARK_THEME_QSS


def setup_logging() -> None:
    """Configure structured console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    """Main application lifecycle entry point."""
    setup_logging()

    # Enable High DPI pixmaps
    app = QApplication(sys.argv)
    app.setApplicationName("A3 Overhead Book Scanner")
    app.setOrganizationName("DeepaDS")

    # Apply professional dark theme
    app.setStyleSheet(DARK_THEME_QSS)

    window = MainWindow()

    # Check for optional CLI flags
    if "--mock" in sys.argv:
        # Auto-connect to mock mode if passed
        window.camera_panel.mode_combo.setCurrentIndex(1)
        window._start_camera("mock", 0)

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

