"""Main Application Window integrating ModernWindow, NavigationView and pages."""

from __future__ import annotations

import os
from typing import Any

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from pyside6_modern_widgets import ModernWindow, NavigationPosition, NavigationView

from ..config import config
from ..constants import APP_NAME, APP_VERSION
from ..core.scheduler import scheduler
from .components.desktop_notification import get_desktop_notification
from .components.tray_icon import AppTrayIcon, create_default_tray_icon
from .icons import create_icon
from .theme import force_window_light_mode
from .pages.favorites_page import FavoritesPage
from .pages.gallery_page import GalleryPage
from .pages.history_page import HistoryPage
from .pages.random_page import RandomSwitcherPage
from .pages.scheduler_page import SchedulerPage
from .pages.settings_page import SettingsPage


class MainWindow(ModernWindow):
    """Modern Desktop Wallpaper Application Main Window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1240, 780)
        self.setMinimumSize(1000, 620)
        self.setWindowIcon(create_default_tray_icon())

        self._init_ui()
        self._init_tray()
        self._init_events()

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

        # Collapse sidebar by default on startup
        if hasattr(self.nav_view, "sidebar"):
            self.nav_view.sidebar.setCollapsed(True, animated=False)

        self.setCentralWidget(self.nav_view)

        # Hook page refresh on tab switch
        self.nav_view.currentChanged.connect(self._on_page_changed)

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

        # Connect history auto-refresh on wallpaper applied
        scheduler.wallpaper_applied.connect(lambda _: self.history_page.refresh())

        # Start auto-rotation scheduler if enabled
        scheduler.start_if_enabled()

    def _on_page_changed(self, index: int) -> None:
        current_page = self.nav_view.widget(index)
        if current_page == self.favorites_page:
            self.favorites_page.refresh()
        elif current_page == self.history_page:
            self.history_page.refresh()

    def _trigger_next_wallpaper(self) -> None:
        scheduler.trigger_switch(source=config.auto_switch_source)

    def _apply_specific_wallpaper(self, item_data: dict[str, Any]) -> None:
        scheduler.trigger_switch(specific_item=item_data)

    def _show_and_activate(self) -> None:
        self.showNormal()
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
        scheduler.stop()
        self.close()
        QApplication.quit()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        force_window_light_mode(int(self.winId()))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if getattr(self, "_is_quitting", False):
            event.accept()
            return

        if config.close_to_tray and hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            get_desktop_notification().show_success(f"{APP_NAME}已最小化到系统托盘", "双击托盘图标可重新打开主窗口")
        else:
            self._is_quitting = True
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.hide()
            scheduler.stop()
            event.accept()
            QApplication.quit()

