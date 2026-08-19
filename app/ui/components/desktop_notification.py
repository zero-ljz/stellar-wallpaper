"""Custom desktop floating notification message with live progress tracking."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...config import config
from ...constants import APP_NAME
from ...core.scheduler import scheduler
from ..icons import create_fluent_pixmap, create_icon


class DesktopNotification(QWidget):
    """Custom floating desktop notification widget for wallpaper progress and status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setFixedSize(360, 96)

        self._init_ui()
        self._init_animations()
        self._init_timer()
        self._connect_scheduler()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)

        # Card Frame
        self.card = QFrame(self)
        self.card.setObjectName("NotificationCard")
        self.card.setStyleSheet("""
            QFrame#NotificationCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(6)

        # Top Header: Icon + Title + Close Button
        header = QHBoxLayout()
        header.setSpacing(8)

        self.icon_label = QLabel(self.card)
        self.icon_label.setPixmap(create_fluent_pixmap("sparkle_filled", color="#0078D4", size=18))
        header.addWidget(self.icon_label)

        self.title_label = QLabel(APP_NAME, self.card)
        font = self.title_label.font()
        font.setBold(True)
        font.setPointSize(12)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #0F172A;")
        header.addWidget(self.title_label, 1)

        self.close_btn = QPushButton(self.card)
        self.close_btn.setIcon(create_icon("close", color="#94A3B8", size=12))
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #F1F5F9;
            }
        """)
        self.close_btn.clicked.connect(self.hide_animated)
        header.addWidget(self.close_btn)
        card_layout.addLayout(header)

        # Stage status message
        self.message_label = QLabel("正在准备更换壁纸...", self.card)
        self.message_label.setStyleSheet("color: #334155; font-size: 12px;")
        card_layout.addWidget(self.message_label)

        # Progress bar
        self.progress_bar = QProgressBar(self.card)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 2px;
            }
        """)
        card_layout.addWidget(self.progress_bar)

        # Subtext (file size / percentage / resolution)
        self.subtext_label = QLabel("", self.card)
        self.subtext_label.setStyleSheet("color: #64748B; font-size: 11px;")
        card_layout.addWidget(self.subtext_label)
        self.subtext_label.hide()

        outer_layout.addWidget(self.card)

    def _init_animations(self) -> None:
        self._is_fading_out = False
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(220)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_anim.finished.connect(self._on_fade_animation_finished)

    def _init_timer(self) -> None:
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide_animated)

    def _connect_scheduler(self) -> None:
        scheduler.stage_changed.connect(self._on_stage_changed)
        scheduler.download_progress.connect(self._on_download_progress)
        scheduler.wallpaper_applied.connect(self._on_wallpaper_applied)
        scheduler.error_occurred.connect(self._on_switch_error)

    def _reposition(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        margin = 16
        x = geo.right() - self.width() - margin
        y = geo.bottom() - self.height() - margin
        self.move(x, y)

    def show_stage(self, stage_text: str, percent: int = 0, subtext: str = "") -> None:
        if not config.tray_notifications:
            return
        self._auto_hide_timer.stop()
        self._reposition()

        self.icon_label.setPixmap(create_fluent_pixmap("sparkle_filled", color="#0078D4", size=18))
        self.title_label.setText("正在更换壁纸")
        self.message_label.setText(stage_text)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(percent)

        if subtext:
            self.subtext_label.setVisible(True)
            self.subtext_label.setText(subtext)
        else:
            self.subtext_label.hide()

        self.card.setStyleSheet("""
            QFrame#NotificationCard {
                background-color: #FFFFFF;
                border: 1px solid #BFDBFE;
                border-radius: 10px;
            }
        """)

        self._is_fading_out = False
        self.icon_label.setPixmap(create_fluent_pixmap("sparkle_filled", color="#0078D4", size=18))
        if not self.isVisible() or self.windowOpacity() < 0.9:
            self.setWindowOpacity(0.0)
            self.show()
            self._fade_anim.stop()
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.start()

    def show_success(self, title: str, subtext: str = "") -> None:
        if not config.tray_notifications:
            return
        self._reposition()

        self.icon_label.setPixmap(create_fluent_pixmap("check_circle_filled", color="#10B981", size=18))
        self.title_label.setText("壁纸已更新")
        self.message_label.setText(title)
        self.progress_bar.setVisible(False)

        if subtext:
            self.subtext_label.setVisible(True)
            self.subtext_label.setText(subtext)
        else:
            self.subtext_label.hide()

        self.card.setStyleSheet("""
            QFrame#NotificationCard {
                background-color: #FFFFFF;
                border: 1px solid #86EFAC;
                border-radius: 10px;
            }
        """)

        self._is_fading_out = False
        if not self.isVisible() or self.windowOpacity() < 0.9:
            self.setWindowOpacity(0.0)
            self.show()
            self._fade_anim.stop()
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.start()

        self._auto_hide_timer.start(3500)

    def show_error(self, err_msg: str) -> None:
        if not config.tray_notifications:
            return
        self._reposition()

        self.icon_label.setPixmap(create_fluent_pixmap("warning_filled", color="#EF4444", size=18))
        self.title_label.setText("壁纸设置失败")
        self.message_label.setText(err_msg)
        self.progress_bar.setVisible(False)
        self.subtext_label.hide()

        self.card.setStyleSheet("""
            QFrame#NotificationCard {
                background-color: #FFFFFF;
                border: 1px solid #FCA5A5;
                border-radius: 10px;
            }
        """)

        self._is_fading_out = False
        if not self.isVisible() or self.windowOpacity() < 0.9:
            self.setWindowOpacity(0.0)
            self.show()
            self._fade_anim.stop()
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.start()

        self._auto_hide_timer.start(5000)

    def hide_animated(self) -> None:
        self._is_fading_out = True
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_animation_finished(self) -> None:
        if getattr(self, "_is_fading_out", False) and self.windowOpacity() <= 0.05:
            self.hide()
            self._is_fading_out = False

    # Scheduler signal handlers
    def _on_stage_changed(self, stage: str) -> None:
        self.show_stage(stage)

    def _on_download_progress(self, current: int, total: int, percent: int) -> None:
        cur_mb = current / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        sub = f"{cur_mb:.1f} MB / {tot_mb:.1f} MB ({percent}%)" if total > 0 else f"{cur_mb:.1f} MB"
        self.show_stage("正在下载高清原图...", percent, sub)

    def _on_wallpaper_applied(self, item: dict[str, Any]) -> None:
        title = item.get("title") or item.get("category_name") or "精选壁纸"
        cat = item.get("category_name") or ""
        res = item.get("resolution") or ""
        sub = f"分类: {cat}  |  分辨率: {res}".strip(" |")
        self.show_success(title, sub)

    def _on_switch_error(self, err: str) -> None:
        self.show_error(err)


_notification_instance: DesktopNotification | None = None


def get_desktop_notification() -> DesktopNotification:
    """Returns the global desktop notification instance, creating it if needed."""
    global _notification_instance
    if _notification_instance is None:
        _notification_instance = DesktopNotification()
    return _notification_instance

