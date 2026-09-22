"""Main entrypoint for Stellar Wallpaper Application."""

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication
from pyside6_modern_widgets.i18n import load_translator

from app.constants import APP_ID, APP_NAME
from app.core.single_instance import SingleInstance
from app.ui.main_window import MainWindow
from app.ui.theme import apply_fusion_light_theme


def main() -> int:
    # Enable High DPI scaling and crisp pixmaps
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)  # keep running in tray

    single_instance = SingleInstance(APP_ID)
    if not single_instance.is_primary:
        return 0

    # Apply Fusion style in Light mode
    apply_fusion_light_theme(app)

    # Install component library Chinese translations
    translator = load_translator("zh_CN", app)
    if translator is not None:
        app.installTranslator(translator)

    # Initialize Main Window
    window = MainWindow()
    single_instance.activation_requested.connect(window._show_and_activate)
    window.show()
    if single_instance.take_pending_activation():
        QTimer.singleShot(0, window._show_and_activate)

    result = app.exec()
    single_instance.close()
    return result


if __name__ == "__main__":
    sys.exit(main())
