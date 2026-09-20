"""Global search box widget for the modern title bar."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit, QWidget

from ..icons import create_icon


class TitleBarSearchBox(QLineEdit):
    """Modern Fluent-styled search box designed for the custom title bar."""

    search_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBarSearchBox")
        self.setPlaceholderText("搜索壁纸 (Ctrl+F)...")
        self.setToolTip("搜索超高清壁纸（回车键搜索，快捷键 Ctrl+F）")
        self.setFixedSize(170, 28)

        # Leading search action with Fluent search icon
        self.search_action = self.addAction(
            create_icon("search", "#64748B", size=16),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search_action.setToolTip("点击搜索")
        self.search_action.triggered.connect(self._emit_search)

        # Custom Trailing dismiss (clear) action - cleanly centered vector icon
        self.clear_action = self.addAction(
            create_icon("dismiss", "#94A3B8", size=16),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self.clear_action.setToolTip("清空")
        self.clear_action.setVisible(False)
        self.clear_action.triggered.connect(self._on_clear_clicked)

        self.textChanged.connect(self._on_text_changed)
        self.returnPressed.connect(self._emit_search)

        self.setStyleSheet("""
            QLineEdit#TitleBarSearchBox {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 2px 4px;
                color: #0F172A;
                font-size: 12px;
                font-weight: 500;
            }
            QLineEdit#TitleBarSearchBox:hover {
                background-color: #F8FAFC;
                border-color: #94A3B8;
            }
            QLineEdit#TitleBarSearchBox:focus {
                background-color: #FFFFFF;
                border: 1.5px solid #0078D4;
            }
            QLineEdit#TitleBarSearchBox QToolButton {
                border: none;
                background-color: transparent;
                border-radius: 4px;
                padding: 0px;
                margin: 0px 2px;
            }
            QLineEdit#TitleBarSearchBox QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.08);
            }
        """)

    def _on_text_changed(self, text: str) -> None:
        self.clear_action.setVisible(bool(text))

    def _on_clear_clicked(self) -> None:
        self.clear()
        self.search_requested.emit("")

    def _emit_search(self) -> None:
        text = self.text().strip()
        self.search_requested.emit(text)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self.text():
                self.clear()
                self.search_requested.emit("")
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)
