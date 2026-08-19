"""Modern progress HUD and Toast notification component."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


from ..icons import create_fluent_pixmap, create_icon


class ProgressHUD(QFrame):
    """A sleek floating progress HUD / notification card for status and progress feedback."""

    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ProgressHUD")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QFrame#ProgressHUD {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
        """)

        self._init_ui()
        self._init_animation()
        self._init_timer()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Header row: Status Icon + Message + Close
        header = QHBoxLayout()
        header.setSpacing(8)

        self.icon_label = QLabel(self)
        self.icon_label.setPixmap(create_fluent_pixmap("sparkle_filled", color="#0078D4", size=18))

        self.message_label = QLabel("准备更换壁纸...", self)
        font = self.message_label.font()
        font.setBold(True)
        self.message_label.setFont(font)
        self.message_label.setStyleSheet("color: #1F2937;")

        self.close_btn = QPushButton(self)
        self.close_btn.setIcon(create_icon("close", color="#9CA3AF", size=12))
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("""
            QPushButton { border: none; background: transparent; }
            QPushButton:hover { background: #F3F4F6; border-radius: 4px; }
        """)
        self.close_btn.clicked.connect(self.hide_animated)

        header.addWidget(self.icon_label)
        header.addWidget(self.message_label, 1)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #F3F4F6;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Details subtext
        self.subtext_label = QLabel("", self)
        self.subtext_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(self.subtext_label)

    def show_progress(self, message: str, percent: int = 0, subtext: str = "") -> None:
        """Show HUD in active progress state."""
        self._auto_hide_timer.stop()
        self.icon_label.setPixmap(create_fluent_pixmap("sparkle_filled", color="#0078D4", size=18))
        self.message_label.setText(message)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(percent)
        self.subtext_label.setVisible(bool(subtext))
        self.subtext_label.setText(subtext)
        self.setStyleSheet("""
            QFrame#ProgressHUD {
                background-color: #FFFFFF;
                border: 1px solid #0078D4;
                border-radius: 8px;
            }
        """)
        self.show()
        self.raise_()

    def show_success(self, message: str, subtext: str = "", auto_hide_ms: int = 3500) -> None:
        """Show HUD in success state and auto-dismiss."""
        self.icon_label.setPixmap(create_fluent_pixmap("check_circle_filled", color="#10B981", size=18))
        self.message_label.setText(message)
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.subtext_label.setVisible(bool(subtext))
        self.subtext_label.setText(subtext)
        self.setStyleSheet("""
            QFrame#ProgressHUD {
                background-color: #F0FDF4;
                border: 1px solid #86EFAC;
                border-radius: 8px;
            }
        """)
        self.show()
        self.raise_()
        self._auto_hide_timer.start(auto_hide_ms)

    def show_error(self, message: str, subtext: str = "", auto_hide_ms: int = 5000) -> None:
        """Show HUD in error state and auto-dismiss."""
        self.icon_label.setPixmap(create_fluent_pixmap("warning_filled", color="#EF4444", size=18))
        self.message_label.setText(message)
        self.progress_bar.setVisible(False)
        self.subtext_label.setVisible(bool(subtext))
        self.subtext_label.setText(subtext)
        self.setStyleSheet("""
            QFrame#ProgressHUD {
                background-color: #FEF2F2;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
            }
        """)
        self.show()
        self.raise_()
        self._auto_hide_timer.start(auto_hide_ms)

    def update_progress(self, percent: int, subtext: str = "") -> None:
        """Update current progress percentage and subtext."""
        self.progress_bar.setValue(percent)
        if subtext:
            self.subtext_label.setVisible(True)
            self.subtext_label.setText(subtext)

    def hide_animated(self) -> None:
        self.hide()
        self.closed.emit()
