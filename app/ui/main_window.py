"""Main Application Window integrating ModernWindow, NavigationView and pages."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLayout, QPushButton, QWidget
from pyside6_modern_widgets import (
    ModernMenuBar,
    ModernWindow,
    NavigationPosition,
    NavigationView,
)

from ..config import config
from ..constants import APP_NAME, APP_VERSION
from ..core.scheduler import scheduler
from .components.desktop_notification import get_desktop_notification
from .components.message_box import open_directory
from .components.title_search_box import TitleBarSearchBox
from .components.tray_icon import AppTrayIcon, create_default_tray_icon
from .icons import create_icon
from .pages.favorites_page import FavoritesPage
from .pages.gallery_page import GalleryPage
from .pages.history_page import HistoryPage
from .pages.random_page import RandomSwitcherPage
from .pages.scheduler_page import SchedulerPage
from .pages.settings_page import SettingsPage
from .theme import force_window_light_mode


class MainWindow(ModernWindow):
    """Modern Desktop Wallpaper Application Main Window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowIcon(create_default_tray_icon())
        self.setTitleAlignment("center")
        self._was_maximized_before_tray = False

        self._init_ui()
        window_layout = self.layout()
        if window_layout is not None:
            window_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.setMinimumWidth(850)
        self.resize(930, 650)
        self._init_tray()
        self._init_events()

    def showMaximized(self) -> None:
        """Preserve the normal geometry when maximizing."""
        if not self.isMaximized():
            geometry = self.geometry()
            if geometry.isValid():
                self._normal_geometry_before_maximize = QRect(geometry)
        super().showMaximized()

    def showNormal(self) -> None:
        """Restore the geometry captured before maximization."""
        super().showNormal()
        geometry = getattr(self, "_normal_geometry_before_maximize", None)
        if isinstance(geometry, QRect) and geometry.isValid():
            self.setGeometry(geometry)
        self._normal_geometry_before_maximize = None

    def _is_native_maximized(self) -> bool:
        """Report the Win32 maximize state for title-bar state checks."""
        if sys.platform != "win32":
            return self.isMaximized()
        return bool(ctypes.windll.user32.IsZoomed(int(self.winId())))

    def _init_ui(self) -> None:
        # Initialize floating desktop notification service
        self.notification = get_desktop_notification()

        # NavigationView from pyside6-modern-widgets as central widget
        self.nav_view = NavigationView(self)

        # Style contentContainer to match modern rounded corners on Windows 10/11
        if hasattr(self.nav_view, "contentContainer"):
            self.nav_view.contentContainer.setStyleSheet("""
                QFrame#NavigationContent {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-top-left-radius: 10px;
                    border-bottom-right-radius: 10px;
                }
            """)

        # Instantiate Pages
        self.gallery_page = GalleryPage(self.nav_view)
        self.random_page = RandomSwitcherPage(self.nav_view)
        self.scheduler_page = SchedulerPage(self.nav_view)
        self.favorites_page = FavoritesPage(self.nav_view)
        self.history_page = HistoryPage(self.nav_view)
        self.settings_page = SettingsPage(self.nav_view)

        # Add Pages to NavigationView with Vector Icons
        self.nav_view.addPage(
            self.gallery_page,
            "探索发现",
            icon=create_icon("gallery", "#475569"),
            selected=True,
        )
        self.nav_view.addPage(
            self.random_page,
            "随机切换",
            icon=create_icon("shuffle", "#475569"),
        )
        self.nav_view.addPage(
            self.scheduler_page,
            "定时更换",
            icon=create_icon("timer", "#475569"),
        )
        self.nav_view.addPage(
            self.favorites_page,
            "我的收藏",
            icon=create_icon("heart", "#475569"),
        )
        self.nav_view.addPage(
            self.history_page,
            "历史记录",
            icon=create_icon("history", "#475569"),
        )
        self.nav_view.addPage(
            self.settings_page,
            "设置中心",
            icon=create_icon("settings", "#475569"),
            position=NavigationPosition.BOTTOM,
        )

        self._init_menu_bar()
        self._init_title_bar_controls()

        # Collapse sidebar by default on startup
        if hasattr(self.nav_view, "sidebar"):
            self.nav_view.sidebar.setCollapsed(True, animated=False)

        self.setCentralWidget(self.nav_view)

        # Hook page refresh on tab switch
        self.nav_view.currentChanged.connect(self._on_page_changed)

    def _init_menu_bar(self) -> None:
        self.menu_bar = ModernMenuBar(self)
        self.menu_bar.setNativeMenuBar(False)

        wallpaper_menu = self.menu_bar.addMenu("壁纸(&W)")
        self.next_wallpaper_action = wallpaper_menu.addAction(
            create_icon("shuffle", "#475569", size=16),
            "切换下一张壁纸",
        )
        self.next_wallpaper_action.triggered.connect(self._trigger_next_wallpaper)

        self.auto_rotation_action = wallpaper_menu.addAction(
            create_icon("timer", "#475569", size=16),
            "自动轮播",
        )
        self.auto_rotation_action.setCheckable(True)
        self.auto_rotation_action.setChecked(scheduler.is_running)
        self.auto_rotation_action.triggered.connect(self._set_auto_rotation_enabled)
        wallpaper_menu.aboutToShow.connect(self._sync_menu_bar_state)

        view_menu = self.menu_bar.addMenu("视图(&V)")
        self.navigation_action_group = QActionGroup(self)
        self.navigation_action_group.setExclusive(False)
        self.navigation_actions: list[QAction] = []
        page_entries = (
            ("探索发现", "gallery"),
            ("随机切换", "shuffle"),
            ("定时更换", "timer"),
            ("我的收藏", "heart"),
            ("历史记录", "history"),
            ("设置中心", "settings"),
        )
        for index, (title, icon_name) in enumerate(page_entries):
            action = view_menu.addAction(create_icon(icon_name, "#475569", size=16), title)
            action.setCheckable(True)
            action.setChecked(index == self.nav_view.currentIndex())
            action.triggered.connect(
                lambda _checked=False, target=index: self._select_navigation_page(target)
            )
            self.navigation_action_group.addAction(action)
            self.navigation_actions.append(action)
        view_menu.aboutToShow.connect(self._sync_navigation_menu_state)

        program_menu = self.menu_bar.addMenu("程序(&P)")
        open_folder_action = program_menu.addAction(
            create_icon("folder", "#475569", size=16),
            "打开壁纸保存目录",
        )
        open_folder_action.triggered.connect(self._open_download_dir)
        settings_action = program_menu.addAction(
            create_icon("settings", "#475569", size=16),
            "设置中心",
        )
        settings_action.triggered.connect(self._open_settings)
        program_menu.addSeparator()
        quit_action = program_menu.addAction(
            create_icon("power", "#DC2626", size=16),
            "退出程序",
        )
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.force_quit)

        if self.titleBar is not None:
            self.titleBar.addCustomWidget(self.menu_bar, align="left")

    def _init_title_bar_controls(self) -> None:
        # Quick wallpaper actions in title bar
        self.title_next_btn = QPushButton(self)
        self.title_next_btn.setObjectName("TitleBarNextBtn")
        self.title_next_btn.setIcon(create_icon("shuffle", "#475569", size=15))
        self.title_next_btn.setToolTip("切换下一张壁纸 (随机抽取)")
        self.title_next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_next_btn.clicked.connect(self._trigger_next_wallpaper)

        self.title_auto_rotate_btn = QPushButton(self)
        self.title_auto_rotate_btn.setObjectName("TitleBarAutoRotateBtn")
        self.title_auto_rotate_btn.setCheckable(True)
        self.title_auto_rotate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sync_auto_rotation_btn_state(scheduler.is_running)
        self.title_auto_rotate_btn.clicked.connect(self._toggle_auto_rotation)

        self.title_folder_btn = QPushButton(self)
        self.title_folder_btn.setObjectName("TitleBarFolderBtn")
        self.title_folder_btn.setIcon(create_icon("folder", "#475569", size=15))
        self.title_folder_btn.setToolTip("打开壁纸保存目录")
        self.title_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_folder_btn.clicked.connect(self._open_download_dir)

        # Global search box
        self.title_search_box = TitleBarSearchBox(self)
        self.title_search_box.search_requested.connect(self._on_global_search)

        # Subtle left margin on first tool button to visually separate from menu bar
        self.title_next_btn.setStyleSheet("margin-left: 6px;")

        if self.titleBar is not None:
            self.titleBar.addCustomWidget(self.title_next_btn, align="left")
            self.titleBar.addCustomWidget(self.title_auto_rotate_btn, align="left")
            self.titleBar.addCustomWidget(self.title_folder_btn, align="left")
            self.titleBar.addCustomWidget(self.title_search_box, align="right")

        self.search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.search_shortcut.activated.connect(self._focus_search_box)

    def _toggle_auto_rotation(self) -> None:
        if scheduler.is_running:
            scheduler.stop()
        else:
            scheduler.start()

    def _sync_auto_rotation_btn_state(self, is_running: bool) -> None:
        if not hasattr(self, "title_auto_rotate_btn"):
            return
        self.title_auto_rotate_btn.setChecked(is_running)
        if is_running:
            self.title_auto_rotate_btn.setIcon(create_icon("pause", "#0078D4", size=15))
            self.title_auto_rotate_btn.setToolTip("自动轮播运行中（点击暂停）")
        else:
            self.title_auto_rotate_btn.setIcon(create_icon("play", "#475569", size=15))
            self.title_auto_rotate_btn.setToolTip("开启自动轮播")

    def _focus_search_box(self) -> None:
        self.title_search_box.setFocus()
        self.title_search_box.selectAll()

    def _on_global_search(self, kw: str) -> None:
        self._select_navigation_page(0)
        if kw:
            self.gallery_page.search_keyword(kw)
        else:
            self.gallery_page.reset_search()

    def _sync_search_box_text(self, text: str) -> None:
        if self.title_search_box.text() != text:
            self.title_search_box.setText(text)

    def _init_tray(self) -> None:
        self.tray_icon = AppTrayIcon(self)
        self.tray_icon.show_main_window_requested.connect(self._show_and_activate)
        self.tray_icon.open_settings_requested.connect(self._open_settings)
        self.tray_icon.switch_next_requested.connect(self._trigger_next_wallpaper)
        self.tray_icon.quit_requested.connect(self.force_quit)
        self.tray_icon.show()

    def _init_events(self) -> None:
        # Connect gallery and other pages apply requests
        self.gallery_page.apply_wallpaper_requested.connect(self._apply_specific_wallpaper)
        self.favorites_page.apply_wallpaper_requested.connect(self._apply_specific_wallpaper)
        self.history_page.apply_wallpaper_requested.connect(self._apply_specific_wallpaper)

        # Connect gallery search synchronization with title bar search box
        self.gallery_page.search_applied.connect(self._sync_search_box_text)
        self.gallery_page.search_cleared.connect(self.title_search_box.clear)

        # Connect history auto-refresh on wallpaper applied
        scheduler.wallpaper_applied.connect(lambda _: self.history_page.refresh())

        # Start auto-rotation scheduler if enabled
        scheduler.status_changed.connect(self.auto_rotation_action.setChecked)
        scheduler.status_changed.connect(self._sync_auto_rotation_btn_state)
        scheduler.start_if_enabled()

        app_instance = QApplication.instance()
        if app_instance is not None:
            app_instance.aboutToQuit.connect(scheduler.shutdown)

    def _select_navigation_page(self, index: int) -> None:
        self.nav_view.setCurrentIndex(index)
        self._sync_navigation_actions(index)

    def _sync_navigation_actions(self, current_index: int) -> None:
        for i, action in enumerate(self.navigation_actions):
            action.setChecked(i == current_index)

    def _sync_navigation_menu_state(self) -> None:
        self._sync_navigation_actions(self.nav_view.currentIndex())

    def _on_page_changed(self, index: int) -> None:
        self._sync_navigation_actions(index)
        current_page = self.nav_view.widget(index)
        if current_page == self.favorites_page:
            self.favorites_page.refresh()
        elif current_page == self.history_page:
            self.history_page.refresh()

    def _trigger_next_wallpaper(self) -> None:
        scheduler.trigger_switch(source=config.auto_switch_source)

    def _set_auto_rotation_enabled(self, enabled: bool) -> None:
        if enabled == scheduler.is_running:
            return
        if enabled:
            scheduler.start()
        else:
            scheduler.stop()

    def _sync_menu_bar_state(self) -> None:
        self.auto_rotation_action.setChecked(scheduler.is_running)
        self._sync_auto_rotation_btn_state(scheduler.is_running)

    def _open_download_dir(self) -> None:
        path = Path(config.download_dir)
        path.mkdir(parents=True, exist_ok=True)
        open_directory(path)

    def _apply_specific_wallpaper(self, item_data: dict[str, Any]) -> None:
        scheduler.trigger_switch(specific_item=item_data)

    def _show_and_activate(self) -> None:
        restore_maximized = self._was_maximized_before_tray or self.isMaximized()
        if not self.isVisible() or self.isMinimized():
            if restore_maximized:
                self.showMaximized()
            else:
                self.showNormal()
        self._was_maximized_before_tray = False
        self.activateWindow()
        self.raise_()

    def _open_settings(self) -> None:
        for i in range(self.nav_view.count()):
            if self.nav_view.widget(i) == self.settings_page:
                self.nav_view.setCurrentIndex(i)
                break
        self._show_and_activate()

    def force_quit(self) -> None:
        """Explicitly quit the application without minimizing to tray."""
        self._is_quitting = True
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.hide()
        scheduler.shutdown()
        self.close()
        QApplication.quit()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        force_window_light_mode(int(self.winId()))

    def closeEvent(self, event: QCloseEvent) -> None:
        if getattr(self, "_is_quitting", False):
            event.accept()
            return

        if config.close_to_tray and hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self._was_maximized_before_tray = self.isMaximized()
            self.hide()
            event.ignore()
            get_desktop_notification().show_success(f"{APP_NAME}已最小化到系统托盘", "双击托盘图标可重新打开主窗口")
        else:
            self._is_quitting = True
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.hide()
            scheduler.shutdown()
            event.accept()
            QApplication.quit()
