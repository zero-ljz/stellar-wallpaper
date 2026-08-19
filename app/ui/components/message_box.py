"""Modern Light Fusion message box and notification dialogs."""

from __future__ import annotations

import ctypes
import sys
from ctypes import byref, c_int, sizeof
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..icons import create_fluent_pixmap, create_icon


def force_window_light_mode(hwnd: int) -> None:
    """Explicitly forces Windows DWM to render light mode on the given window handle."""
    if sys.platform == "win32":
        try:
            dark_value = c_int(0)  # 0 = Light mode (False)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                20,  # DWMWA_USE_IMMERSIVE_DARK_MODE
                byref(dark_value),
                sizeof(dark_value),
            )
        except Exception:
            pass


class ModernMessageBox(QDialog):
    """Clean, high-contrast, pure Light Fusion dialog."""

    def __init__(
        self,
        title: str,
        message: str,
        dialog_type: str = "info",  # "info", "success", "warning", "question"
        parent: QWidget | None = None,
        confirm_mode: bool = False,
        ok_text: str = "确定",
        cancel_text: str = "取消",
        open_folder_path: Path | str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self.setMaximumWidth(540)
        self.confirm_mode = confirm_mode
        self.open_folder_path = Path(open_folder_path) if open_folder_path else None

        self._init_ui(title, message, dialog_type, ok_text, cancel_text)

    def _init_ui(
        self,
        title: str,
        message: str,
        dialog_type: str,
        ok_text: str,
        cancel_text: str,
    ) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(18)

        # Header Row: Icon + Title
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        icon_label = QLabel(self)
        icon_label.setFixedSize(36, 36)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if dialog_type == "success":
            icon_label.setPixmap(create_fluent_pixmap("check_circle_filled", color="#10B981", size=24))
            badge_bg = "#ECFDF5"
        elif dialog_type == "warning":
            icon_label.setPixmap(create_fluent_pixmap("warning_filled", color="#F59E0B", size=24))
            badge_bg = "#FFFBEB"
        elif dialog_type == "question":
            icon_label.setPixmap(create_fluent_pixmap("question", color="#0078D4", size=24))
            badge_bg = "#EFF6FF"
        else:
            icon_label.setPixmap(create_fluent_pixmap("info_filled", color="#0078D4", size=24))
            badge_bg = "#EFF6FF"

        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                border-radius: 18px;
                border: none;
            }}
        """)
        header_row.addWidget(icon_label)

        title_lbl = QLabel(title, self)
        font = title_lbl.font()
        font.setPointSize(14)
        font.setBold(True)
        title_lbl.setFont(font)
        title_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        header_row.addWidget(title_lbl, 1)

        layout.addLayout(header_row)

        # Message Content
        msg_lbl = QLabel(message, self)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        msg_lbl.setStyleSheet("""
            QLabel {
                color: #334155;
                font-size: 13px;
                font-weight: 500;
                line-height: 1.5;
                border: none;
                background: transparent;
                padding-left: 2px;
            }
        """)
        layout.addWidget(msg_lbl)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        if self.open_folder_path:
            open_btn = QPushButton("打开所在目录", self)
            open_btn.setIcon(create_icon("folder", color="#334155", size=15))
            open_btn.setFixedHeight(34)
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 13px;
                    padding: 0 14px;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                    border-color: #94A3B8;
                    color: #0F172A;
                }
            """)
            open_btn.clicked.connect(self._on_open_folder)
            btn_row.addWidget(open_btn)

        if self.confirm_mode:
            cancel_btn = QPushButton(cancel_text, self)
            cancel_btn.setFixedHeight(34)
            cancel_btn.setMinimumWidth(80)
            cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #334155;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 13px;
                    padding: 0 16px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    border-color: #94A3B8;
                    color: #0F172A;
                }
            """)
            cancel_btn.clicked.connect(self.reject)
            btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton(ok_text, self)
        ok_btn.setFixedHeight(34)
        ok_btn.setMinimumWidth(80)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: 1px solid #0078D4;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                padding: 0 18px;
            }
            QPushButton:hover {
                background-color: #1084D9;
                border-color: #1084D9;
            }
            QPushButton:pressed {
                background-color: #0067B8;
                border-color: #0067B8;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    def _on_open_folder(self) -> None:
        if self.open_folder_path:
            open_directory(self.open_folder_path)
            self.accept()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        force_window_light_mode(int(self.winId()))


def open_directory(file_path: Path | str) -> None:
    """Opens Windows Explorer with the specific file selected, or opens parent directory."""
    p = Path(file_path).resolve()
    if sys.platform == "win32":
        try:
            if p.exists():
                import subprocess
                subprocess.Popen(["explorer", f"/select,{p}"])
            elif p.parent.exists():
                import os
                os.startfile(str(p.parent))
        except Exception as e:
            print(f"Error opening directory for {p}: {e}")
            try:
                import os
                os.startfile(str(p.parent))
            except Exception:
                pass


def show_info(parent: QWidget | None, title: str, message: str) -> None:
    """Shows a crisp Light Fusion information dialog."""
    dlg = ModernMessageBox(title, message, dialog_type="info", parent=parent)
    dlg.exec()


def show_success(parent: QWidget | None, title: str, message: str) -> None:
    """Shows a crisp Light Fusion success dialog."""
    dlg = ModernMessageBox(title, message, dialog_type="success", parent=parent)
    dlg.exec()


def show_save_success(parent: QWidget | None, file_path: Path | str, title: str = "保存成功") -> None:
    """Shows a crisp Light Fusion success dialog when saving wallpaper with 1-click open directory button."""
    path_obj = Path(file_path).resolve()
    dlg = ModernMessageBox(
        title=title,
        message=f"壁纸已成功保存至:\n{path_obj}",
        dialog_type="success",
        parent=parent,
        ok_text="确定",
        open_folder_path=path_obj,
    )
    dlg.exec()


def show_warning(parent: QWidget | None, title: str, message: str) -> None:
    """Shows a crisp Light Fusion warning dialog."""
    dlg = ModernMessageBox(title, message, dialog_type="warning", parent=parent)
    dlg.exec()


def show_question(
    parent: QWidget | None,
    title: str,
    message: str,
    ok_text: str = "确定",
    cancel_text: str = "取消",
) -> bool:
    """Shows a crisp Light Fusion confirmation dialog, returning True if accepted."""
    dlg = ModernMessageBox(
        title,
        message,
        dialog_type="question",
        parent=parent,
        confirm_mode=True,
        ok_text=ok_text,
        cancel_text=cancel_text,
    )
    return dlg.exec() == QDialog.DialogCode.Accepted
