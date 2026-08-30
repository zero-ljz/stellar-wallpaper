"""Regression tests for tray restoration and wallpaper card badges."""

import sys
from typing import Any, cast

from PySide6.QtCore import QSize
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from pyside6_modern_widgets import ModernWindow

from app.ui.components.wallpaper_card import WallpaperCard
from app.ui.main_window import MainWindow


def get_qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication(sys.argv)


class WindowStub:
    def __init__(self, was_maximized: bool) -> None:
        self._was_maximized_before_tray = was_maximized
        self.maximized = was_maximized
        self.visible = False
        self.minimized = False
        self.calls: list[str] = []

    def isMaximized(self) -> bool:
        return self.maximized

    def isVisible(self) -> bool:
        return self.visible

    def isMinimized(self) -> bool:
        return self.minimized

    def showMaximized(self) -> None:
        self.maximized = True
        self.visible = True
        self.minimized = False
        self.calls.append("showMaximized")

    def showNormal(self) -> None:
        self.maximized = False
        self.visible = True
        self.minimized = False
        self.calls.append("showNormal")

    def activateWindow(self) -> None:
        self.calls.append("activateWindow")

    def raise_(self) -> None:
        self.calls.append("raise")


def test_tray_restore_preserves_maximized_state() -> None:
    window = WindowStub(was_maximized=True)

    MainWindow._show_and_activate(cast(Any, window))

    assert window.calls == ["showMaximized", "activateWindow", "raise"]
    assert window._was_maximized_before_tray is False

    MainWindow._show_and_activate(cast(Any, window))

    assert window.calls[-2:] == ["activateWindow", "raise"]
    assert window.maximized is True


def test_tray_restore_preserves_normal_state() -> None:
    window = WindowStub(was_maximized=False)

    MainWindow._show_and_activate(cast(Any, window))

    assert window.calls == ["showNormal", "activateWindow", "raise"]


def test_initial_window_uses_compact_default_size() -> None:
    get_qapp()

    class LightweightMainWindow(MainWindow):
        def _init_ui(self) -> None:
            pass

        def _init_tray(self) -> None:
            pass

        def _init_events(self) -> None:
            pass

    window = LightweightMainWindow()

    assert window.size() == QSize(930, 650)
    assert window.minimumWidth() == 850
    assert window.minimumHeight() == 0


def test_tray_restore_keeps_title_bar_in_restore_state() -> None:
    app = get_qapp()

    class LightweightMainWindow(MainWindow):
        def __init__(self) -> None:
            ModernWindow.__init__(self)
            self._was_maximized_before_tray = False

    window = LightweightMainWindow()
    window.resize(1000, 620)
    window.show()
    app.processEvents()
    normal_geometry = window.geometry()
    assert window.titleBar is not None

    for _ in range(5):
        window.titleBar.maximizeButton.click()
        QTest.qWait(50)
        if sys.platform == "win32":
            assert window._is_native_maximized()
        assert window.isMaximized()
        assert window.geometry() != normal_geometry

        window.titleBar.maximizeButton.click()
        QTest.qWait(50)
        if sys.platform == "win32":
            assert not window._is_native_maximized()
        assert not window.isMaximized()
        assert window.geometry() == normal_geometry

    window.showMaximized()
    QTest.qWait(50)
    window.hide()
    app.processEvents()
    window._was_maximized_before_tray = True

    window._show_and_activate()
    app.processEvents()

    assert window.isMaximized()
    assert window.titleBar.maximizeButton.toolTip() == "向下还原"

    window.titleBar.maximizeButton.click()
    QTest.qWait(150)
    assert not window.isMaximized()
    if sys.platform == "win32":
        assert not window._is_native_maximized()
    assert window.geometry() == normal_geometry

    window._show_and_activate()
    app.processEvents()
    assert not window.isMaximized()
    window.close()


def test_minimized_maximized_window_restores_its_normal_geometry() -> None:
    app = get_qapp()

    class LightweightMainWindow(MainWindow):
        def __init__(self) -> None:
            ModernWindow.__init__(self)
            self._was_maximized_before_tray = False

    window = LightweightMainWindow()
    window.resize(1000, 620)
    window.show()
    app.processEvents()
    normal_geometry = window.geometry()

    window.showMaximized()
    app.processEvents()
    window.showMinimized()
    app.processEvents()
    window._show_and_activate()
    app.processEvents()
    window.titleBar.maximizeButton.click()
    QTest.qWait(150)

    assert not window.isMaximized()
    assert window.geometry() == normal_geometry
    window.close()


def test_wallpaper_badges_use_translucent_backgrounds(monkeypatch) -> None:
    _app = get_qapp()
    monkeypatch.setattr(WallpaperCard, "_load_thumbnail", lambda self: None)

    card = WallpaperCard({"category_name": "游戏壁纸", "resolution": "3840x2160"})

    assert "rgba(51, 65, 85, 0.25)" in card.cat_badge.styleSheet()
    assert "rgba(56, 139, 202, 0.28)" in card.res_badge.styleSheet()
