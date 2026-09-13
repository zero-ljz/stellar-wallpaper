"""Regression tests for the application-wide theme policy."""

import sys

from PySide6.QtWidgets import QApplication
from pyside6_modern_widgets import ThemeMode, theme_manager

from app.ui.theme import apply_fusion_light_theme


def get_qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication(sys.argv)


def test_application_theme_is_pinned_to_light_mode() -> None:
    app = get_qapp()

    apply_fusion_light_theme(app)

    manager = theme_manager()
    assert manager.mode() is ThemeMode.LIGHT
    assert not manager.isDark()
    assert manager.theme().name == "light"
