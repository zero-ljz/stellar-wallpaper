"""Polished history page displaying previously applied wallpapers with modern pagination."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...constants import WALLPAPER_CACHE_DIR
from ...core.database import db
from ..components.message_box import show_question
from ..components.preview_dialog import PreviewDialog
from ..components.wallpaper_card import WallpaperCard, extract_item_ids
from ..icons import create_fluent_pixmap, create_icon


class HistoryPage(QWidget):
    """Page displaying historical applied wallpapers with high-performance pagination."""

    apply_wallpaper_requested = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[WallpaperCard] = []
        self._current_cols = 0
        self._page_size = 24
        self._current_page = 1
        self._total_count = 0
        self._total_pages = 1

        self._init_ui()
        self.load_page(1)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 16)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title_row = QHBoxLayout()
        title_lbl = QLabel("历史记录", self)
        font = title_lbl.font()
        font.setPointSize(16)
        font.setBold(True)
        title_lbl.setFont(font)
        title_row.addWidget(title_lbl)

        self.count_badge = QLabel("0 条", self)
        self.count_badge.setStyleSheet("""
            background-color: #F1F5F9;
            color: #475569;
            font-weight: 600;
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 10px;
            border: none;
        """)
        title_row.addWidget(self.count_badge)

        title_row.addStretch()
        title_box.addLayout(title_row)

        desc_lbl = QLabel("自动记录曾应用到桌面的所有壁纸，支持随时回溯翻阅并重新应用", self)
        desc_lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 12px;")
        title_box.addWidget(desc_lbl)
        header.addLayout(title_box)

        header.addStretch()

        self.open_folder_btn = QPushButton("打开壁纸目录", self)
        self.open_folder_btn.setIcon(create_icon("folder", color="#475569", size=16))
        self.open_folder_btn.setToolTip("在文件资源管理器中打开历史壁纸缓存文件夹")
        self.open_folder_btn.setFixedHeight(36)
        self.open_folder_btn.clicked.connect(self._open_folder)
        header.addWidget(self.open_folder_btn)

        self.clear_btn = QPushButton("清空历史", self)
        self.clear_btn.setIcon(create_icon("trash", color="#475569", size=16))
        self.clear_btn.setFixedHeight(36)
        self.clear_btn.clicked.connect(self._clear_history)
        header.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton("刷新", self)
        self.refresh_btn.setIcon(create_icon("refresh", color="#475569", size=16))
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.clicked.connect(lambda: self.load_page(self._current_page))
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
        self.empty_card.setObjectName("HistoryEmptyCard")
        self.empty_card.setStyleSheet("""
            QFrame#HistoryEmptyCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        empty_layout = QVBoxLayout(self.empty_card)
        empty_layout.setContentsMargins(40, 60, 40, 60)
        empty_layout.setSpacing(10)

        empty_icon = QLabel(self.empty_card)
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setPixmap(create_fluent_pixmap("history", color="#94A3B8", size=48))
        empty_icon.setStyleSheet("border: none; background: transparent;")
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("暂无历史记录", self.empty_card)
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = empty_title.font()
        font.setPointSize(15)
        font.setBold(True)
        empty_title.setFont(font)
        empty_title.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel("当您手动或通过定时轮播更换壁纸后，此处将自动记录更换的壁纸与时间", self.empty_card)
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_desc.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px; border: none; background: transparent;")
        empty_layout.addWidget(empty_desc)

        layout.addWidget(self.empty_card)
        self.empty_card.hide()

        # Bottom Modern Pagination Bar
        self.page_bar_widget = QWidget(self)
        page_bar = QHBoxLayout(self.page_bar_widget)
        page_bar.setContentsMargins(4, 4, 4, 4)
        page_bar.setSpacing(10)
        page_bar.addStretch()

        self.prev_btn = QPushButton("上一页", self.page_bar_widget)
        self.prev_btn.setIcon(create_icon("chevron_left", color="#475569", size=16))
        self.prev_btn.clicked.connect(self._prev_page)
        page_bar.addWidget(self.prev_btn)

        self.page_info_label = QLabel("第 1 / 1 页 (共 0 条)", self.page_bar_widget)
        self.page_info_label.setStyleSheet("color: #334155; font-weight: 600; font-size: 12px;")
        page_bar.addWidget(self.page_info_label)

        self.next_btn = QPushButton("下一页", self.page_bar_widget)
        self.next_btn.setIcon(create_icon("chevron_right", color="#475569", size=16))
        self.next_btn.clicked.connect(self._next_page)
        page_bar.addWidget(self.next_btn)

        page_bar.addSpacing(16)

        jump_lbl = QLabel("跳至", self.page_bar_widget)
        jump_lbl.setStyleSheet("color: #334155; font-weight: 600; font-size: 12px;")
        page_bar.addWidget(jump_lbl)

        self.jump_spinbox = QSpinBox(self.page_bar_widget)
        self.jump_spinbox.setMinimum(1)
        self.jump_spinbox.setMaximum(1)
        self.jump_spinbox.setValue(1)
        self.jump_spinbox.setFixedWidth(72)
        self.jump_spinbox.setFixedHeight(34)
        page_bar.addWidget(self.jump_spinbox)

        self.jump_btn = QPushButton("跳转", self.page_bar_widget)
        self.jump_btn.setIcon(create_icon("arrow_jump", color="#475569", size=14))
        self.jump_btn.setFixedHeight(34)
        self.jump_btn.clicked.connect(self._jump_page)
        page_bar.addWidget(self.jump_btn)

        page_bar.addStretch()
        layout.addWidget(self.page_bar_widget)

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

    def load_page(self, page_num: int) -> None:
        self._total_count = db.count_history()
        self._total_pages = max(1, math.ceil(self._total_count / self._page_size))
        self._current_page = max(1, min(page_num, self._total_pages))
        offset = (self._current_page - 1) * self._page_size

        for card in self._cards:
            card.deleteLater()
        self._cards.clear()
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._current_cols = 0

        self.count_badge.setText(f"{self._total_count} 条")

        if self._total_count == 0:
            self.empty_card.show()
            self.clear_btn.setEnabled(False)
            self.page_bar_widget.hide()
            return

        self.empty_card.hide()
        self.clear_btn.setEnabled(True)
        self.page_bar_widget.show()

        # Update pagination controls
        self.page_info_label.setText(
            f"第 {self._current_page} / {self._total_pages} 页 (共 {self._total_count} 条)"
        )
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)
        self.jump_spinbox.setMaximum(self._total_pages)
        self.jump_spinbox.setValue(self._current_page)

        items = db.get_history(limit=self._page_size, offset=offset)
        for item_data in items:
            card = WallpaperCard(item_data, self.container)
            card.apply_requested.connect(self.apply_wallpaper_requested.emit)
            card.preview_requested.connect(self._on_preview)
            self._cards.append(card)

        self._relayout_grid(force=True)

    def refresh(self) -> None:
        self.load_page(self._current_page)

    def _prev_page(self) -> None:
        if self._current_page > 1:
            self.load_page(self._current_page - 1)

    def _next_page(self) -> None:
        if self._current_page < self._total_pages:
            self.load_page(self._current_page + 1)

    def _jump_page(self) -> None:
        target = self.jump_spinbox.value()
        if 1 <= target <= self._total_pages:
            self.load_page(target)

    def _on_preview(self, item_data: dict[str, Any]) -> None:
        dialog = PreviewDialog(item_data, self)
        dialog.apply_requested.connect(self.apply_wallpaper_requested.emit)
        dialog.exec()
        for card in self._cards:
            wid, url = extract_item_ids(card.item_data)
            fav = db.is_favorite(wid, url)
            if card._is_favorited != fav:
                card._is_favorited = fav
                card._update_fav_style()

    def _open_folder(self) -> None:
        path = Path(WALLPAPER_CACHE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))

    def _clear_history(self) -> None:
        if show_question(self, "确认清空", "确定要清空所有历史记录吗？"):
            db.clear_history()
            self.load_page(1)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout_grid()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._relayout_grid()
