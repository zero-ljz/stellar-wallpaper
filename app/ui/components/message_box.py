"""Message helpers backed by pyside6-modern-widgets dialogs."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton, QPushButton, QWidget
from pyside6_modern_widgets import ModernMessageBox

from ..icons import create_fluent_pixmap, create_icon


def open_directory(file_path: Path | str) -> None:
    """Open a directory or select a specific file in Windows Explorer."""
    path = Path(file_path).resolve()
    if sys.platform != "win32":
        return

    try:
        if path.is_dir():
            import os

            os.startfile(str(path))
        elif path.exists():
            import subprocess

            subprocess.Popen(["explorer", f"/select,{path}"])
        elif path.parent.exists():
            import os

            os.startfile(str(path.parent))
    except OSError as exc:
        print(f"Error opening directory for {path}: {exc}")


def _create_message_box(
    parent: QWidget | None,
    title: str,
    message: str,
    dialog_type: str,
    *,
    ok_text: str = "确定",
    cancel_text: str | None = None,
    open_folder_path: Path | str | None = None,
) -> tuple[ModernMessageBox, QPushButton, QPushButton | None, QAbstractButton | None]:
    dialog_parent = parent.window() if isinstance(parent, QWidget) else parent
    box = ModernMessageBox(parent=dialog_parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard
        | Qt.TextInteractionFlag.LinksAccessibleByMouse
    )
    box.setMinimumWidth(380)
    box.setMaximumWidth(560)

    icon_name, icon_color = {
        "success": ("check_circle_filled", "#10B981"),
        "warning": ("warning_filled", "#F59E0B"),
        "question": ("question", "#0078D4"),
        "info": ("info_filled", "#0078D4"),
    }.get(dialog_type, ("info_filled", "#0078D4"))
    box.setIconPixmap(create_fluent_pixmap(icon_name, color=icon_color, size=28))

    open_button: QAbstractButton | None = None
    if open_folder_path is not None:
        open_button = box.addButton(
            "打开所在目录", ModernMessageBox.ButtonRole.ActionRole
        )
        open_button.setIcon(create_icon("folder", color="#334155", size=15))
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #0B0F19;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                border-color: #94A3B8;
                color: #0F172A;
            }
            QPushButton:pressed {
                background-color: #E2E8F0;
            }
        """)

    cancel_button: QPushButton | None = None
    if cancel_text is not None:
        cancel_button = box.addButton(
            cancel_text, ModernMessageBox.ButtonRole.RejectRole
        )
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                border-color: #94A3B8;
                color: #0F172A;
            }
            QPushButton:pressed {
                background-color: #E2E8F0;
            }
        """)
        box.setEscapeButton(cancel_button)

    ok_button = box.addButton(ok_text, ModernMessageBox.ButtonRole.AcceptRole)
    ok_button.setCursor(Qt.CursorShape.PointingHandCursor)
    ok_button.setStyleSheet("""
        QPushButton {
            background-color: #0078D4;
            color: #FFFFFF;
            border: 1px solid #0078D4;
            border-radius: 6px;
            font-weight: 600;
            font-size: 13px;
            padding: 6px 20px;
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
    box.setDefaultButton(ok_button)
    return box, ok_button, cancel_button, open_button


def _exec_message_box(
    parent: QWidget | None,
    title: str,
    message: str,
    dialog_type: str,
    *,
    ok_text: str = "确定",
    cancel_text: str | None = None,
    open_folder_path: Path | str | None = None,
) -> bool:
    box, ok_button, _cancel_button, open_button = _create_message_box(
        parent,
        title,
        message,
        dialog_type,
        ok_text=ok_text,
        cancel_text=cancel_text,
        open_folder_path=open_folder_path,
    )
    box.exec()
    clicked = box.clickedButton()
    if clicked is open_button and open_folder_path is not None:
        open_directory(open_folder_path)
    return clicked is ok_button


def show_info(parent: QWidget | None, title: str, message: str) -> None:
    _exec_message_box(parent, title, message, "info")


def show_success(parent: QWidget | None, title: str, message: str) -> None:
    _exec_message_box(parent, title, message, "success")


def show_save_success(
    parent: QWidget | None, file_path: Path | str, title: str = "保存成功"
) -> None:
    path = Path(file_path).resolve()
    _exec_message_box(
        parent,
        title,
        f"壁纸已成功保存至:\n{path}",
        "success",
        open_folder_path=path,
    )


def show_batch_download_result(
    parent: QWidget | None,
    directory: Path | str,
    downloaded: int,
    skipped: int,
    failed: int,
    cancelled: bool = False,
) -> None:
    parts = [f"成功下载 {downloaded} 张"]
    if skipped:
        parts.append(f"已存在并跳过 {skipped} 张")
    if failed:
        parts.append(f"失败 {failed} 张")
    if cancelled:
        parts.append("任务已取消")
    _exec_message_box(
        parent,
        "批量下载完成" if not cancelled else "批量下载已停止",
        "，".join(parts) + f"。\n保存目录：\n{Path(directory).resolve()}",
        "success" if failed == 0 and not cancelled else "warning",
        open_folder_path=directory,
    )


def show_warning(parent: QWidget | None, title: str, message: str) -> None:
    _exec_message_box(parent, title, message, "warning")


def show_question(
    parent: QWidget | None,
    title: str,
    message: str,
    ok_text: str = "确定",
    cancel_text: str = "取消",
) -> bool:
    return _exec_message_box(
        parent,
        title,
        message,
        "question",
        ok_text=ok_text,
        cancel_text=cancel_text,
    )
