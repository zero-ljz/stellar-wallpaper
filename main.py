"""Main entrypoint for Stellar Wallpaper Application."""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.constants import APP_NAME
from app.ui.main_window import MainWindow
from app.ui.theme import apply_fusion_light_theme


def main() -> int:
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)  # keep running in tray

    # Apply Fusion style in Light mode
    apply_fusion_light_theme(app)

    # Initialize Main Window
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
