"""Regression tests for the application-wide theme policy."""

import sys

from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from pyside6_modern_widgets import ModernMenuBar, ModernWindow, ThemeMode, theme_manager

from app.ui.theme import apply_fusion_light_theme, load_application_fonts


def get_qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication(sys.argv)


def test_application_font_loads_lxgw_wenkai_lite() -> None:
    app = get_qapp()
    family = load_application_fonts()
    assert family == "LXGW WenKai Lite"

    apply_fusion_light_theme(app)
    assert app.font().family() == "LXGW WenKai Lite"


def test_application_theme_is_pinned_to_light_mode() -> None:
    app = get_qapp()

    apply_fusion_light_theme(app)

    manager = theme_manager()
    assert manager.mode() is ThemeMode.LIGHT
    assert not manager.isDark()
    assert manager.theme().name == "light"


def _images_differ(first: QImage, second: QImage) -> bool:
    if first.size() != second.size():
        return True
    return any(
        first.pixel(x, y) != second.pixel(x, y)
        for y in range(first.height())
        for x in range(first.width())
    )


def test_inactive_window_fades_title_and_menu_text() -> None:
    app = get_qapp()
    apply_fusion_light_theme(app)

    window = ModernWindow()
    window.resize(700, 300)
    window.setWindowTitle("Title Probe")
    menu_bar = ModernMenuBar(window)
    menu_bar.addMenu("Menu Probe")
    assert window.titleBar is not None
    window.titleBar.addCustomWidget(menu_bar, align="left")
    other_window = QWidget()

    try:
        window.show()
        window.activateWindow()
        window.raise_()
        QTest.qWait(100)
        assert window.isActiveWindow()
        active_title = window.titleBar.titleLabel.grab().toImage()
        active_menu = menu_bar.grab().toImage()

        other_window.show()
        other_window.activateWindow()
        other_window.raise_()
        QTest.qWait(100)
        assert not window.isActiveWindow()
        inactive_title = window.titleBar.titleLabel.grab().toImage()
        inactive_menu = menu_bar.grab().toImage()

        assert _images_differ(active_title, inactive_title)
        assert _images_differ(active_menu, inactive_menu)
    finally:
        window.close()
        other_window.close()
