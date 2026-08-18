"""Polished favorites collection page."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...config import config
from ...core.database import db
from ..components.preview_dialog import PreviewDialog
from ..components.wallpaper_card import WallpaperCard


class FavoritesPage(QWidget):
    """Page displaying user's starred/favorited wallpapers."""

    apply_wallpaper_requested = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[WallpaperCard] = []
        self._current_cols = 0

        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 16)
        layout.setSpacing(14)

        # Header Bar
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title_row = QHBoxLayout()
        title_lbl = QLabel("❤️ 我的收藏", self)
        font = title_lbl.font()
        font.setPointSize(16)
        font.setBold(True)
        title_lbl.setFont(font)
        title_row.addWidget(title_lbl)

        self.count_badge = QLabel("0 张", self)
        self.count_badge.setStyleSheet("""
            background-color: #FEF2F2;
            color: #EF4444;
            font-weight: 600;
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 10px;
            border: none;
        """)
        title_row.addWidget(self.count_badge)

        title_row.addStretch()
        title_box.addLayout(title_row)

        desc_lbl = QLabel("收藏您心仪的高清壁纸，支持随时一键设为桌面壁纸或加入轮播池", self)
        desc_lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 12px;")
        title_box.addWidget(desc_lbl)
        header.addLayout(title_box)

        header.addStretch()

        self.random_fav_btn = QPushButton("⚡ 从收藏中随机应用", self)
        self.random_fav_btn.setProperty("class", "PrimaryButton")
        self.random_fav_btn.setFixedHeight(36)
        self.random_fav_btn.clicked.connect(self._apply_random_favorite)
        header.addWidget(self.random_fav_btn)

        self.open_dir_btn = QPushButton("📂 打开保存目录", self)
        self.open_dir_btn.setFixedHeight(36)
        self.open_dir_btn.clicked.connect(self._open_download_dir)
        header.addWidget(self.open_dir_btn)

        self.refresh_btn = QPushButton("🔄 刷新", self)
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)

        layout.addLayout(header)

        # Grid Scroll Area
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll.viewport().setStyleSheet("background: transparent; border: none;")
        self.container = QWidget(self.scroll)
        self.container.setStyleSheet("background: transparent; border: none;")
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(0, 4, 0, 4)
        self.grid.setSpacing(16)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        # Empty state card
        self.empty_card = QFrame(self)
        self.empty_card.setObjectName("FavoritesEmptyCard")
        self.empty_card.setStyleSheet("""
            QFrame#FavoritesEmptyCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        empty_layout = QVBoxLayout(self.empty_card)
        empty_layout.setContentsMargins(40, 60, 40, 60)
        empty_layout.setSpacing(10)

        empty_icon = QLabel("🌟", self.empty_card)
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = empty_icon.font()
        font.setPointSize(36)
        empty_icon.setFont(font)
        empty_icon.setStyleSheet("border: none; background: transparent;")
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("暂无收藏壁纸", self.empty_card)
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = empty_title.font()
        font.setPointSize(15)
        font.setBold(True)
        empty_title.setFont(font)
        empty_title.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel("在「探索发现」画廊或「随机切换」页面中，点击卡片右上角的 ★ 即可将喜欢的美图加入收藏夹", self.empty_card)
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_desc.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px; border: none; background: transparent;")
        empty_layout.addWidget(empty_desc)

        layout.addWidget(self.empty_card)
        self.empty_card.hide()

    def _calculate_cols(self) -> int:
        vp_width = self.scroll.viewport().width()
        scroll_w = self.scroll.width()
        page_w = self.width() - 48

        width = vp_width if (vp_width > 50 and abs(vp_width - scroll_w) <= 30) else max(scroll_w, page_w, 300)
        card_total_width = 264 + 16
        return max(2, (width + 16) // card_total_width)

    def _relayout_grid(self, force: bool = False) -> None:
        if not self._cards:
            return
        cols = self._calculate_cols()
        if not force and cols == self._current_cols:
            return
        self._current_cols = cols

        while self.grid.count():
            self.grid.takeAt(0)

        for idx, card in enumerate(self._cards):
            row = idx // cols
            col = idx % cols
            self.grid.addWidget(card, row, col)

    def refresh(self) -> None:
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._current_cols = 0

        items = db.get_favorites(limit=200)
        self.count_badge.setText(f"{len(items)} 张")

        if not items:
            self.empty_card.show()
            self.random_fav_btn.setEnabled(False)
            return

        self.empty_card.hide()
        self.random_fav_btn.setEnabled(True)

        for item_data in items:
            card = WallpaperCard(item_data, self.container)
            card.apply_requested.connect(self.apply_wallpaper_requested.emit)
            card.preview_requested.connect(self._on_preview)
            card.favorite_toggled.connect(lambda _, is_fav: self.refresh() if not is_fav else None)
            self._cards.append(card)

        self._relayout_grid(force=True)

    def _on_preview(self, item_data: dict[str, Any]) -> None:
        dialog = PreviewDialog(item_data, self)
        dialog.apply_requested.connect(self.apply_wallpaper_requested.emit)
        dialog.exec()
        self.refresh()

    def _apply_random_favorite(self) -> None:
        fav = db.get_random_favorite()
        if fav:
            self.apply_wallpaper_requested.emit(fav)
        else:
            QMessageBox.information(self, "提示", "收藏夹为空，无法设置壁纸")

    def _open_download_dir(self) -> None:
        path = Path(config.download_dir)
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout_grid()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._relayout_grid()
