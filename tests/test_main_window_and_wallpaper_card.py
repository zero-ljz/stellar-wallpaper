"""Regression tests for tray restoration and wallpaper card badges."""

import sys
from typing import Any, cast

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from pyside6_modern_widgets import ModernMenu, ModernMenuBar, ModernWindow

from app.config import config
from app.ui.components.tray_icon import AppTrayIcon
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


def test_main_window_uses_title_bar_menu_and_centered_title(monkeypatch) -> None:
    get_qapp()
    monkeypatch.setattr(
        "app.ui.main_window.GalleryPage.load_page", lambda _self, _page: None
    )

    class LightweightMainWindow(MainWindow):
        def _init_tray(self) -> None:
            pass

        def _init_events(self) -> None:
            pass

    window = LightweightMainWindow()

    assert isinstance(window.menu_bar, ModernMenuBar)
    assert [action.text() for action in window.menu_bar.actions()] == [
        "壁纸(&W)",
        "视图(&V)",
        "程序(&P)",
    ]
    assert all(
        isinstance(action.menu(), ModernMenu) for action in window.menu_bar.actions()
    )
    assert window.titleAlignment() == "center"
    assert window.titleBar is not None
    assert window.titleBar.titleLabel.alignment() & Qt.AlignmentFlag.AlignHCenter

    assert not window.navigation_action_group.isExclusive()
    assert window.navigation_actions[0].isChecked()

    window.navigation_actions[3].trigger()
    assert window.nav_view.currentIndex() == 3
    assert window.navigation_actions[3].isChecked()
    assert not window.navigation_actions[0].isChecked()

    # Repeated trigger should keep active page checked instead of toggling off
    window.navigation_actions[3].trigger()
    assert window.navigation_actions[3].isChecked()

    # Nav view index change should synchronize checked state across menu actions
    window.nav_view.setCurrentIndex(1)
    assert window.navigation_actions[1].isChecked()
    assert not window.navigation_actions[3].isChecked()

    window.hide()


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
    assert window.titleBar.maximizeButton.toolTip() in ("向下还原", "还原", "Restore")

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


def test_tray_uses_component_library_modern_menu() -> None:
    get_qapp()

    tray = AppTrayIcon()

    assert isinstance(tray.contextMenu(), ModernMenu)
    tray.hide()


def test_wallpaper_badges_use_translucent_backgrounds(monkeypatch) -> None:
    _app = get_qapp()
    monkeypatch.setattr(WallpaperCard, "_load_thumbnail", lambda self: None)

    card = WallpaperCard({"category_name": "游戏壁纸", "resolution": "3840x2160"})

    assert "rgba(51, 65, 85, 0.25)" in card.cat_badge.styleSheet()
    assert "rgba(56, 139, 202, 0.28)" in card.res_badge.styleSheet()


def test_wallpaper_card_selection_mode(monkeypatch) -> None:
    _app = get_qapp()
    monkeypatch.setattr(WallpaperCard, "_load_thumbnail", lambda self: None)
    card = WallpaperCard({"id": "42", "download_url": "https://example.com/42.jpg"})
    changes = []
    card.selection_changed.connect(
        lambda item, selected: changes.append((item["id"], selected))
    )

    card.set_selection_mode(True)
    assert card.selection_checkbox.isVisibleTo(card)
    card.set_selected(True, emit=True)

    assert card.is_selected()
    assert card.selection_checkbox.isChecked()
    assert "2px solid #0078D4" in card.styleSheet()
    assert changes == [("42", True)]

    card.set_selection_mode(False)
    assert not card.is_selected()


def test_title_bar_tool_buttons(monkeypatch) -> None:
    get_qapp()
    monkeypatch.setitem(config._config, "last_wallpaper", None)
    monkeypatch.setattr(
        "app.ui.main_window.GalleryPage.load_page", lambda _self, _page: None
    )

    class LightweightMainWindow(MainWindow):
        def _init_tray(self) -> None:
            pass

    window = LightweightMainWindow()
    assert hasattr(window, "title_next_btn")
    assert hasattr(window, "title_auto_rotate_btn")
    assert hasattr(window, "title_favorite_btn")
    assert not hasattr(window, "title_folder_btn")
    assert window.titleBar.left_layout.indexOf(window.title_next_btn) >= 0
    assert window.titleBar.left_layout.indexOf(window.title_auto_rotate_btn) >= 0
    assert window.titleBar.left_layout.indexOf(window.title_favorite_btn) >= 0
    assert window.titleBar.left_layout.indexOf(window.menu_bar) < window.titleBar.left_layout.indexOf(window.title_next_btn)
    assert not window.title_favorite_btn.isEnabled()
    assert window.title_favorite_btn.toolTip() == "暂无可收藏的当前壁纸"

    # Test trigger next wallpaper
    triggered = []
    monkeypatch.setattr(
        "app.ui.main_window.scheduler.trigger_switch",
        lambda source: triggered.append(source),
    )
    window.title_next_btn.click()
    assert len(triggered) == 1

    # Test toggle auto rotation
    starts = []
    stops = []
    monkeypatch.setattr("app.ui.main_window.scheduler.start", lambda: starts.append(True))
    monkeypatch.setattr("app.ui.main_window.scheduler.stop", lambda: stops.append(True))
    from app.core.scheduler import scheduler
    scheduler._is_running = False

    window.title_auto_rotate_btn.click()
    assert len(starts) == 1

    scheduler._is_running = True
    window.title_auto_rotate_btn.click()
    assert len(stops) == 1
    scheduler._is_running = False

    # Test status changed synchronizes button
    window._sync_auto_rotation_btn_state(True)
    assert window.title_auto_rotate_btn.isChecked()
    assert "暂停" in window.title_auto_rotate_btn.toolTip()

    window._sync_auto_rotation_btn_state(False)
    assert not window.title_auto_rotate_btn.isChecked()
    assert "开启" in window.title_auto_rotate_btn.toolTip()

    window.hide()


def test_title_bar_favorite_button_toggles_current_wallpaper(monkeypatch) -> None:
    get_qapp()
    item = {"id": "42", "title": "银河", "url": "https://example.com/42.jpg"}
    state = {"favorited": False}
    added = []
    removed = []
    notices = []

    monkeypatch.setitem(config._config, "last_wallpaper", item)
    monkeypatch.setattr(
        "app.ui.main_window.GalleryPage.load_page", lambda _self, _page: None
    )
    monkeypatch.setattr(
        "app.ui.main_window.db.is_favorite", lambda _wid, _url: state["favorited"]
    )
    monkeypatch.setattr(
        "app.ui.main_window.db.add_favorite",
        lambda value: added.append(value) or state.update(favorited=True) or True,
    )
    monkeypatch.setattr(
        "app.ui.main_window.db.remove_favorite",
        lambda wid, url: removed.append((wid, url)) or state.update(favorited=False) or True,
    )

    class LightweightMainWindow(MainWindow):
        def _init_tray(self) -> None:
            pass

    window = LightweightMainWindow()
    monkeypatch.setattr(
        window.notification,
        "show_success",
        lambda title, body: notices.append((title, body)),
    )
    assert window.title_favorite_btn.isEnabled()
    assert not window.title_favorite_btn.isChecked()
    assert window.title_favorite_btn.toolTip() == "收藏当前壁纸"

    window.title_favorite_btn.click()
    assert added == [item]
    assert window.title_favorite_btn.isChecked()
    assert window.title_favorite_btn.toolTip() == "取消收藏当前壁纸"
    assert notices[-1] == ("已加入收藏夹", "银河")

    window.title_favorite_btn.click()
    assert removed == [("42", "https://example.com/42.jpg")]
    assert not window.title_favorite_btn.isChecked()
    assert window.title_favorite_btn.toolTip() == "收藏当前壁纸"
    assert notices[-1] == ("已取消收藏", "银河")

    window.hide()


def test_title_bar_global_search_box(monkeypatch) -> None:
    get_qapp()
    monkeypatch.setattr(
        "app.ui.main_window.GalleryPage.load_page", lambda _self, _page: None
    )

    class LightweightMainWindow(MainWindow):
        def _init_tray(self) -> None:
            pass

    window = LightweightMainWindow()
    assert hasattr(window, "title_search_box")
    assert window.title_search_box is not None
    assert window.titleBar is not None
    assert window.titleBar.right_layout.indexOf(window.title_search_box) >= 0

    # Test clear action visibility and clicking
    assert not window.title_search_box.clear_action.isVisible()
    window.title_search_box.setText("壁纸")
    assert window.title_search_box.clear_action.isVisible()
    window.title_search_box.clear_action.trigger()
    assert window.title_search_box.text() == ""
    assert not window.title_search_box.clear_action.isVisible()

    # Test global search switches to gallery and executes search
    window.nav_view.setCurrentIndex(2)  # switch away to page 2
    assert window.nav_view.currentIndex() == 2

    window.title_search_box.setText("赛博朋克")
    window.title_search_box.search_requested.emit("赛博朋克")

    assert window.nav_view.currentIndex() == 0  # switched back to GalleryPage
    assert window.gallery_page._current_keyword == "赛博朋克"
    assert window.gallery_page.search_input.text() == "赛博朋克"

    # Test gallery search input syncs to title_search_box
    window.gallery_page.search_keyword("自然风光")
    assert window.title_search_box.text() == "自然风光"

    # Test reset search clears title_search_box
    window.gallery_page.reset_search()
    assert window.title_search_box.text() == ""

    # Test Escape key clears text and focus
    window.title_search_box.setText("temp")
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    window.title_search_box.keyPressEvent(event)
    assert window.title_search_box.text() == ""

    window.hide()
