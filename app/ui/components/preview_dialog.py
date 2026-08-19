"""Full wallpaper image preview dialog."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QPoint, QRect, QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...config import config
from ...core.api_client import api_client
from ...core.cache_manager import cache_mgr
from ...core.database import db
from ...core.image_loader import image_loader
from ..icons import create_icon
from .message_box import force_window_light_mode, show_info, show_success, show_warning


def _extract_item_ids(item_data: dict[str, Any]) -> tuple[str, str]:
    wid = str(item_data.get("wallpaper_id") or item_data.get("id") or "")
    url = str(item_data.get("url") or item_data.get("url_mid") or item_data.get("thumb_url") or "")
    return wid, url


class PreviewDialog(QDialog):
    """High-resolution wallpaper preview modal dialog."""

    apply_requested = Signal(dict)

    def __init__(self, item_data: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item_data = dict(item_data)
        self.setWindowTitle("壁纸高清大图预览")
        self.resize(960, 620)
        self.setMinimumSize(800, 500)
        self._pixmap: QPixmap | None = None
        self._init_ui()
        self._load_image()

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left: Large Image Display Area
        self.image_frame = QFrame(self)
        self.image_frame.setObjectName("PreviewImageFrame")
        self.image_frame.setStyleSheet("""
            QFrame#PreviewImageFrame {
                background-color: #1E293B;
                border-radius: 8px;
                border: none;
            }
        """)
        image_layout = QVBoxLayout(self.image_frame)
        image_layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel("正在加载高清原图...", self.image_frame)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("color: #94A3B8; font-size: 14px; border: none; background: transparent;")
        image_layout.addWidget(self.image_label)

        layout.addWidget(self.image_frame, 3)

        # Right: Info & Actions Sidebar
        sidebar = QFrame(self)
        sidebar.setObjectName("PreviewSidebar")
        sidebar.setFixedWidth(290)
        sidebar.setStyleSheet("""
            QFrame#PreviewSidebar {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 18, 18, 18)
        sidebar_layout.setSpacing(12)

        # Title
        raw_title = self.item_data.get("title") or self.item_data.get("tag") or "壁纸详情"
        clean_title = raw_title.replace("_360Wallpaper_", "").replace("_category_", "").replace("_", " ").strip()
        title_label = QLabel(clean_title or "壁纸详情", sidebar)
        font = title_label.font()
        font.setBold(True)
        font.setPointSize(13)
        title_label.setFont(font)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        sidebar_layout.addWidget(title_label)

        # Divider
        divider = QFrame(sidebar)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #E2E8F0; border: none; background-color: #E2E8F0; max-height: 1px;")
        sidebar_layout.addWidget(divider)

        # Metadata rows
        cat_name = self.item_data.get("category_name") or "未分类"
        sidebar_layout.addWidget(self._create_meta_row("分类专区", cat_name))

        resolution = self.item_data.get("resolution") or "自动匹配"
        sidebar_layout.addWidget(self._create_meta_row("分辨率", resolution))

        tag = self.item_data.get("tag") or ""
        if tag:
            clean_tag = tag.replace("_360Wallpaper_", "").replace("_category_", "").replace("_", " ").strip()
            sidebar_layout.addWidget(self._create_meta_row("标签", clean_tag))

        wid = str(self.item_data.get("wallpaper_id") or self.item_data.get("id") or "")
        if wid:
            sidebar_layout.addWidget(self._create_meta_row("壁纸编号", wid))

        sidebar_layout.addStretch()

        # Action Buttons
        self.apply_btn = QPushButton("立即设为壁纸", sidebar)
        self.apply_btn.setIcon(create_icon("desktop", color="#FFFFFF", size=16))
        self.apply_btn.setProperty("class", "PrimaryButton")
        self.apply_btn.clicked.connect(self._on_apply)
        sidebar_layout.addWidget(self.apply_btn)

        self.save_btn = QPushButton("保存到本地", sidebar)
        self.save_btn.setIcon(create_icon("download", color="#475569", size=16))
        self.save_btn.clicked.connect(self._on_save)
        sidebar_layout.addWidget(self.save_btn)

        wid, url = _extract_item_ids(self.item_data)
        is_fav = db.is_favorite(wid, url)
        self.fav_btn = QPushButton("取消收藏" if is_fav else "添加到收藏", sidebar)
        self.fav_btn.setIcon(
            create_icon("star_filled" if is_fav else "star", color="#F59E0B" if is_fav else "#475569", size=16)
        )
        self.fav_btn.clicked.connect(self._on_toggle_fav)
        sidebar_layout.addWidget(self.fav_btn)

        self.close_btn = QPushButton("关闭预览", sidebar)
        self.close_btn.setIcon(create_icon("close", color="#475569", size=14))
        self.close_btn.clicked.connect(self.close)
        sidebar_layout.addWidget(self.close_btn)

        layout.addWidget(sidebar)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        force_window_light_mode(int(self.winId()))

    def _create_meta_row(self, label: str, value: str) -> QWidget:
        w = QWidget(self)
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 3, 0, 3)
        hl.setSpacing(10)
        lbl = QLabel(label, w)
        lbl.setFixedWidth(62)
        lbl.setStyleSheet("color: #475569; font-size: 12px; border: none; background: transparent;")
        val = QLabel(value, w)
        val.setWordWrap(True)
        val.setStyleSheet("color: #0B0F19; font-weight: bold; font-size: 12px; border: none; background: transparent;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hl.addWidget(lbl)
        hl.addWidget(val, 1)
        return w

    def _load_image(self) -> None:
        url = self.item_data.get("url") or self.item_data.get("url_mid") or self.item_data.get("thumb_url") or ""
        local_path = self.item_data.get("local_path", "")
        image_loader.load_full_image(url, local_path, self._on_image_loaded)

    def _on_image_loaded(self, pix: QPixmap) -> None:
        if not pix.isNull():
            self._pixmap = pix
            self._update_display()
        else:
            self.image_label.setText("原图加载失败")

    def _update_display(self) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return
        scaled = self._pixmap.scaled(
            self.image_frame.size() - QSize(10, 10),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_display()

    def _on_apply(self) -> None:
        self.apply_requested.emit(self.item_data)
        self.close()

    def _on_save(self) -> None:
        url = self.item_data.get("url") or self.item_data.get("url_mid") or ""
        save_dir = Path(config.download_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = f"Wallpaper_{self.item_data.get('id', 'pic')}.jpg"
        target = save_dir / filename

        cached = cache_mgr.get_wallpaper_path(url)
        if cached.exists():
            import shutil
            shutil.copy2(cached, target)
            show_success(self, "保存成功", f"壁纸已保存到:\n{target}")
        else:
            ok = api_client.download_image(url, target)
            if ok:
                show_success(self, "保存成功", f"壁纸已保存到:\n{target}")
            else:
                show_warning(self, "保存失败", "保存壁纸失败，请重试")

    def _on_toggle_fav(self) -> None:
        wid, url = _extract_item_ids(self.item_data)
        if db.is_favorite(wid, url):
            db.remove_favorite(wid, url)
            self.fav_btn.setText("添加到收藏")
            self.fav_btn.setIcon(create_icon("star", color="#475569", size=16))
        else:
            db.add_favorite(self.item_data)
            self.fav_btn.setText("取消收藏")
            self.fav_btn.setIcon(create_icon("star_filled", color="#F59E0B", size=16))
