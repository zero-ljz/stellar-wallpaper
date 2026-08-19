"""Modern Microsoft Fluent 2 System Tray Icon & Context Menu."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from ...config import config
from ...constants import APP_NAME, APP_VERSION
from ...core.database import db
from ...core.scheduler import scheduler
from .desktop_notification import get_desktop_notification
from ..icons import create_fluent_pixmap, create_icon


def create_default_tray_icon() -> QIcon:
    """Generates a clean programmatic high-DPI tray icon pixmap."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Blue rounded square
    painter.setBrush(QColor("#0078D4"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)

    # White mountain / wallpaper glyph
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QPolygon

    painter.setBrush(QColor("#FFFFFF"))
    polygon = QPolygon([
        QPoint(6, 24),
        QPoint(14, 12),
        QPoint(20, 20),
        QPoint(24, 16),
        QPoint(26, 24),
    ])
    painter.drawPolygon(polygon)
    painter.drawEllipse(20, 7, 4, 4)
    painter.end()
    return QIcon(pixmap)


class TrayHeaderWidget(QWidget):
    """Modern brand and status header card embedded inside tray popup menu."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(0)

        card = QFrame(self)
        card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 6, 10, 6)
        card_layout.setSpacing(10)

        # App Icon
        icon_lbl = QLabel(card)
        icon_lbl.setPixmap(create_fluent_pixmap("gallery", "#0078D4", size=20))
        icon_lbl.setFixedSize(22, 22)
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        card_layout.addWidget(icon_lbl)

        # Title & Subtitle column
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        title_lbl = QLabel(APP_NAME, card)
        title_lbl.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #0F172A; border: none; background: transparent;"
        )
        title_row.addWidget(title_lbl)

        ver_lbl = QLabel(f"v{APP_VERSION}", card)
        ver_lbl.setStyleSheet(
            "font-size: 10px; color: #0078D4; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 4px; padding: 0 4px; font-weight: 600;"
        )
        title_row.addWidget(ver_lbl)
        title_row.addStretch()
        text_layout.addLayout(title_row)

        status_row = QHBoxLayout()
        status_row.setSpacing(5)
        self.dot_lbl = QLabel("●", card)
        self.dot_lbl.setStyleSheet("font-size: 9px; color: #10B981; border: none; background: transparent;")
        status_row.addWidget(self.dot_lbl)

        self.status_lbl = QLabel("自动轮播运行中", card)
        self.status_lbl.setStyleSheet(
            "font-size: 11px; color: #64748B; border: none; background: transparent; font-weight: 500;"
        )
        status_row.addWidget(self.status_lbl)
        status_row.addStretch()
        text_layout.addLayout(status_row)

        card_layout.addLayout(text_layout)
        layout.addWidget(card)

    def update_status(self, is_running: bool, interval_sec: int) -> None:
        if is_running:
            if interval_sec >= 3600:
                h = interval_sec // 3600
                int_str = f"{h}小时"
            elif interval_sec >= 60:
                m = interval_sec // 60
                int_str = f"{m}分钟"
            else:
                int_str = f"{interval_sec}秒"
            self.dot_lbl.setText("●")
            self.dot_lbl.setStyleSheet("font-size: 9px; color: #10B981; border: none; background: transparent;")
            self.status_lbl.setText(f"自动轮播运行中 ({int_str})")
        else:
            self.dot_lbl.setText("○")
            self.dot_lbl.setStyleSheet("font-size: 9px; color: #94A3B8; border: none; background: transparent;")
            self.status_lbl.setText("自动轮播已暂停")


class ModernTrayMenu(QMenu):
    """Custom QMenu with true transparent rounded corners and Windows 11 DWM support."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import byref, c_int, sizeof

                hwnd = int(self.winId())
                corner_pref = c_int(2)  # DWMWCP_ROUND
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(hwnd),
                    33,  # DWMWA_WINDOW_CORNER_PREFERENCE
                    byref(corner_pref),
                    sizeof(corner_pref),
                )
                light_mode = c_int(0)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(hwnd),
                    20,  # DWMWA_USE_IMMERSIVE_DARK_MODE
                    byref(light_mode),
                    sizeof(light_mode),
                )
            except Exception:
                pass


class AppTrayIcon(QSystemTrayIcon):
    """Manages application tray icon, modern context menu, and notifications."""

    show_main_window_requested = Signal()
    open_settings_requested = Signal()
    switch_next_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setIcon(create_default_tray_icon())
        self.setToolTip(f"{APP_NAME} - 运行中")

        self._init_menu()
        self.activated.connect(self._on_tray_activated)

        # Hook scheduler notifications
        scheduler.wallpaper_applied.connect(self._on_wallpaper_applied)
        scheduler.status_changed.connect(self._on_scheduler_status_changed)

    def _init_menu(self) -> None:
        self.menu = ModernTrayMenu()
        self.menu.setFixedWidth(228)
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 7px 12px 7px 32px;
                border-radius: 6px;
                color: #1E293B;
                font-size: 12.5px;
                font-weight: 500;
                margin: 1px 2px;
            }
            QMenu::item:selected {
                background-color: #F1F5F9;
                color: #0078D4;
                font-weight: 600;
            }
            QMenu::item:disabled {
                color: #94A3B8;
            }
            QMenu::icon {
                left: 10px;
            }
            QMenu::separator {
                height: 1px;
                background-color: #F1F5F9;
                margin: 3px 6px;
            }
        """)

        # 1. Header Card
        self.header_widget = TrayHeaderWidget(self.menu)
        header_action = QWidgetAction(self.menu)
        header_action.setDefaultWidget(self.header_widget)
        self.menu.addAction(header_action)
        self.menu.addSeparator()

        # 2. Main Quick Actions
        self.next_action = self.menu.addAction(create_icon("shuffle", "#0078D4", size=16), "切换下一张壁纸")
        self.next_action.triggered.connect(self.switch_next_requested.emit)

        is_run = scheduler.is_running
        self.toggle_timer_action = self.menu.addAction(
            create_icon("pause_filled" if is_run else "play_filled", "#475569", size=16),
            "暂停自动轮播" if is_run else "开启自动轮播",
        )
        self.toggle_timer_action.triggered.connect(self._toggle_timer)

        self.fav_action = self.menu.addAction(create_icon("star", "#475569", size=16), "收藏当前壁纸")
        self.fav_action.triggered.connect(self._toggle_favorite_current)

        self.menu.addSeparator()

        # 3. Utilities & Navigation
        self.open_folder_action = self.menu.addAction(create_icon("folder", "#475569", size=16), "打开壁纸保存目录")
        self.open_folder_action.triggered.connect(self._open_download_dir)

        self.show_action = self.menu.addAction(create_icon("desktop", "#475569", size=16), "显示主窗口")
        self.show_action.triggered.connect(self.show_main_window_requested.emit)

        self.settings_action = self.menu.addAction(create_icon("settings", "#475569", size=16), "设置中心")
        self.settings_action.triggered.connect(self.open_settings_requested.emit)

        self.menu.addSeparator()

        # 4. Exit Action
        self.quit_action = self.menu.addAction(create_icon("power", "#DC2626", size=16), "退出程序")
        self.quit_action.triggered.connect(self.quit_requested.emit)

        # Dynamic state sync on open
        self.menu.aboutToShow.connect(self._sync_menu_state)

        self.setContextMenu(self.menu)

    def _sync_menu_state(self) -> None:
        """Syncs tray menu header, timer state, and favorite state before showing."""
        is_running = scheduler.is_running
        interval = config.auto_switch_interval
        self.header_widget.update_status(is_running, interval)

        self.toggle_timer_action.setText("暂停自动轮播" if is_running else "开启自动轮播")
        self.toggle_timer_action.setIcon(
            create_icon("pause_filled" if is_running else "play_filled", "#475569", size=16)
        )

        last_item = config.last_wallpaper
        if last_item:
            wid = str(last_item.get("id") or last_item.get("wallpaper_id") or "")
            url = str(last_item.get("url") or last_item.get("url_mid") or last_item.get("thumb_url") or "")
            is_fav = db.is_favorite(wid, url)
            if is_fav:
                self.fav_action.setText("已收藏当前壁纸")
                self.fav_action.setIcon(create_icon("star_filled", "#F59E0B", size=16))
            else:
                self.fav_action.setText("收藏当前壁纸")
                self.fav_action.setIcon(create_icon("star", "#475569", size=16))
            self.fav_action.setEnabled(True)
        else:
            self.fav_action.setText("收藏当前壁纸")
            self.fav_action.setIcon(create_icon("star", "#94A3B8", size=16))
            self.fav_action.setEnabled(False)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_main_window_requested.emit()

    def _toggle_timer(self) -> None:
        if scheduler.is_running:
            scheduler.stop()
        else:
            scheduler.start()
        self._sync_menu_state()

    def _toggle_favorite_current(self) -> None:
        last_item = config.last_wallpaper
        if not last_item:
            return
        wid = str(last_item.get("id") or last_item.get("wallpaper_id") or "")
        url = str(last_item.get("url") or last_item.get("url_mid") or last_item.get("thumb_url") or "")
        if db.is_favorite(wid, url):
            db.remove_favorite(wid, url)
            get_desktop_notification().show_info("已取消收藏", last_item.get("title", "当前壁纸"))
        else:
            db.add_favorite(last_item)
            get_desktop_notification().show_success("已加入收藏夹", last_item.get("title", "当前壁纸"))
        self._sync_menu_state()

    def _on_scheduler_status_changed(self, is_running: bool) -> None:
        self._sync_menu_state()

    def _open_download_dir(self) -> None:
        path = Path(config.download_dir)
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))

    def _on_wallpaper_applied(self, item: dict[str, Any]) -> None:
        self._sync_menu_state()

