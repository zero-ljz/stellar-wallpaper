"""System tray icon and context menu."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from ...config import config
from ...constants import APP_NAME
from ...core.scheduler import scheduler


def create_default_tray_icon() -> QIcon:
    """Generates a clean programmatic tray icon pixmap."""
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



class AppTrayIcon(QSystemTrayIcon):
    """Manages application tray icon, menu actions, and notifications."""

    show_main_window_requested = Signal()
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
        menu = QMenu()
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px 4px;
            }
            QMenu::item {
                padding: 7px 22px;
                border-radius: 5px;
                color: #0B0F19;
                font-size: 13px;
                font-weight: 600;
            }
            QMenu::item:selected {
                background-color: #EFF6FF;
                color: #0078D4;
            }
            QMenu::separator {
                height: 1px;
                background: #E2E8F0;
                margin: 4px 8px;
            }
        """)

        # Next wallpaper
        self.next_action = menu.addAction("⚡ 切换下一张壁纸")
        self.next_action.triggered.connect(self.switch_next_requested.emit)

        # Auto rotation toggle
        self.toggle_timer_action = menu.addAction("⏸️ 暂停自动轮播" if scheduler.is_running else "▶️ 开启自动轮播")
        self.toggle_timer_action.triggered.connect(self._toggle_timer)

        menu.addSeparator()

        # Open download directory
        self.open_folder_action = menu.addAction("📂 打开壁纸保存目录")
        self.open_folder_action.triggered.connect(self._open_download_dir)

        # Show main window
        self.show_action = menu.addAction("🪟 显示主窗口")
        self.show_action.triggered.connect(self.show_main_window_requested.emit)

        menu.addSeparator()

        # Exit
        self.quit_action = menu.addAction("🚪 退出程序")
        self.quit_action.triggered.connect(self.quit_requested.emit)

        self.setContextMenu(menu)

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

    def _on_scheduler_status_changed(self, is_running: bool) -> None:
        self.toggle_timer_action.setText("⏸️ 暂停自动轮播" if is_running else "▶️ 开启自动轮播")

    def _open_download_dir(self) -> None:
        path = Path(config.download_dir)
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))

    def _on_wallpaper_applied(self, item: dict[str, Any]) -> None:
        if config.tray_notifications and self.isVisible():
            title = item.get("title") or item.get("category_name") or "壁纸"
            cat = item.get("category_name") or ""
            res = item.get("resolution") or ""
            msg = f"已更换壁纸: {title}"
            if cat or res:
                msg += f" [{cat} {res}]"
            self.showMessage(APP_NAME, msg, QSystemTrayIcon.MessageIcon.Information, 3000)
