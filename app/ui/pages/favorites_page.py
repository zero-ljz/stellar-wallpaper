"""Polished favorites collection page with modern pagination."""

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
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...config import config
from ...core.database import db
from ...core.download_manager import wallpaper_download_key
from ..batch_download import BatchDownloadWorker
from ..components.message_box import show_batch_download_result, show_info
from ..components.preview_dialog import PreviewDialog
from ..components.wallpaper_card import WallpaperCard
from ..icons import create_fluent_pixmap, create_icon


class FavoritesPage(QWidget):
    """Page displaying user's starred/favorited wallpapers with high-performance pagination."""

    apply_wallpaper_requested = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[WallpaperCard] = []
        self._current_cols = 0
        self._page_size = 24
        self._current_page = 1
        self._total_count = 0
        self._total_pages = 1
        self._batch_worker: BatchDownloadWorker | None = None
        self._batch_result: tuple[int, int, int, bool] | None = None
        self._batch_selection_mode = False
        self._selected_items: dict[str, dict[str, Any]] = {}

        self._init_ui()
        self.load_page(1)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 16)
        layout.setSpacing(14)

        # Header Bar
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title_row = QHBoxLayout()
        title_lbl = QLabel("我的收藏", self)
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

        desc_lbl = QLabel(
            "收藏您心仪的壁纸，支持随时一键设为桌面壁纸或加入轮播池", self
        )
        desc_lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 12px;")
        title_box.addWidget(desc_lbl)
        header.addLayout(title_box)

        header.addStretch()

        self.batch_mode_btn = QPushButton("批量下载", self)
        self.batch_mode_btn.setIcon(create_icon("download", color="#475569", size=16))
        self.batch_mode_btn.setFixedHeight(36)
        self.batch_mode_btn.setEnabled(False)
        self.batch_mode_btn.clicked.connect(self._toggle_batch_mode)
        header.addWidget(self.batch_mode_btn)

        self.random_fav_btn = QPushButton("从收藏中随机应用", self)
        self.random_fav_btn.setIcon(create_icon("play", color="#FFFFFF", size=16))
        self.random_fav_btn.setProperty("class", "PrimaryButton")
        self.random_fav_btn.setFixedHeight(36)
        self.random_fav_btn.clicked.connect(self._apply_random_favorite)
        header.addWidget(self.random_fav_btn)

        self.open_dir_btn = QPushButton("打开保存目录", self)
        self.open_dir_btn.setIcon(create_icon("folder", color="#475569", size=16))
        self.open_dir_btn.setFixedHeight(36)
        self.open_dir_btn.clicked.connect(self._open_download_dir)
        header.addWidget(self.open_dir_btn)

        self.refresh_btn = QPushButton("刷新", self)
        self.refresh_btn.setIcon(create_icon("refresh", color="#475569", size=16))
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.clicked.connect(lambda: self.load_page(self._current_page))
        header.addWidget(self.refresh_btn)

        layout.addLayout(header)

        self.batch_bar = QWidget(self)
        self.batch_bar.setObjectName("FavoritesBatchDownloadBar")
        self.batch_bar.setStyleSheet("""
            QWidget#FavoritesBatchDownloadBar {
                background-color: #EFF6FF;
                border-radius: 6px;
            }
        """)
        batch_layout = QHBoxLayout(self.batch_bar)
        batch_layout.setContentsMargins(12, 6, 8, 6)
        batch_layout.setSpacing(8)

        self.batch_count_label = QLabel("已选择 0 张", self.batch_bar)
        self.batch_count_label.setStyleSheet(
            "color: #0F172A; font-weight: 700; background: transparent;"
        )
        batch_layout.addWidget(self.batch_count_label)

        self.select_page_btn = QPushButton("全选本页", self.batch_bar)
        self.select_page_btn.setIcon(create_icon("check", color="#475569", size=15))
        self.select_page_btn.setFixedHeight(30)
        self.select_page_btn.clicked.connect(self._toggle_select_current_page)
        batch_layout.addWidget(self.select_page_btn)

        self.select_all_btn = QPushButton("全选全部收藏", self.batch_bar)
        self.select_all_btn.setFixedHeight(30)
        self.select_all_btn.clicked.connect(self._toggle_select_all)
        batch_layout.addWidget(self.select_all_btn)

        self.clear_selection_btn = QPushButton("清空", self.batch_bar)
        self.clear_selection_btn.setFixedHeight(30)
        self.clear_selection_btn.clicked.connect(self._clear_batch_selection)
        batch_layout.addWidget(self.clear_selection_btn)

        batch_layout.addStretch()

        self.batch_progress = QProgressBar(self.batch_bar)
        self.batch_progress.setFixedWidth(210)
        self.batch_progress.setFixedHeight(8)
        self.batch_progress.setTextVisible(False)
        self.batch_progress.hide()
        batch_layout.addWidget(self.batch_progress)

        self.cancel_download_btn = QPushButton("取消下载", self.batch_bar)
        self.cancel_download_btn.setIcon(
            create_icon("dismiss", color="#475569", size=15)
        )
        self.cancel_download_btn.setFixedHeight(30)
        self.cancel_download_btn.clicked.connect(self._cancel_batch_download)
        self.cancel_download_btn.hide()
        batch_layout.addWidget(self.cancel_download_btn)

        self.download_selected_btn = QPushButton("下载所选", self.batch_bar)
        self.download_selected_btn.setIcon(
            create_icon("download", color="#FFFFFF", size=15)
        )
        self.download_selected_btn.setProperty("class", "PrimaryButton")
        self.download_selected_btn.setFixedHeight(30)
        self.download_selected_btn.setEnabled(False)
        self.download_selected_btn.clicked.connect(self._start_batch_download)
        batch_layout.addWidget(self.download_selected_btn)

        self.batch_bar.hide()
        layout.addWidget(self.batch_bar)

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
        self.grid.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
        )
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

        empty_icon = QLabel(self.empty_card)
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setPixmap(create_fluent_pixmap("heart", color="#FDA4AF", size=48))
        empty_icon.setStyleSheet("border: none; background: transparent;")
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("暂无收藏壁纸", self.empty_card)
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = empty_title.font()
        font.setPointSize(15)
        font.setBold(True)
        empty_title.setFont(font)
        empty_title.setStyleSheet(
            "border: none; background: transparent; color: #0F172A;"
        )
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel(
            "在「探索发现」画廊或「随机切换」页面中，点击卡片右上角的星标即可将喜欢的美图加入收藏夹",
            self.empty_card,
        )
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_desc.setStyleSheet(
            "color: #475569; font-weight: 600; font-size: 13px; border: none; background: transparent;"
        )
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

        self.page_info_label = QLabel("第 1 / 1 页 (共 0 张)", self.page_bar_widget)
        self.page_info_label.setStyleSheet(
            "color: #334155; font-weight: 600; font-size: 12px;"
        )
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

        width = (
            vp_width
            if (vp_width > 50 and abs(vp_width - scroll_w) <= 30)
            else max(scroll_w, page_w, 300)
        )
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
        batch_busy = self._batch_worker is not None
        self._total_count = db.count_favorites()
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

        self.count_badge.setText(f"{self._total_count} 张")

        if self._selected_items and self._batch_worker is None:
            favorites_by_key = {
                wallpaper_download_key(item): item for item in db.get_favorites()
            }
            self._selected_items = {
                key: favorites_by_key[key]
                for key in self._selected_items
                if key in favorites_by_key
            }

        if self._total_count == 0:
            self.empty_card.show()
            self.random_fav_btn.setEnabled(False)
            self.batch_mode_btn.setEnabled(False)
            if not batch_busy:
                self._set_batch_mode(False)
            self.page_bar_widget.hide()
            return

        self.empty_card.hide()
        self.random_fav_btn.setEnabled(not batch_busy)
        self.batch_mode_btn.setEnabled(not batch_busy)
        self.refresh_btn.setEnabled(not batch_busy)
        self.page_bar_widget.show()

        # Update pagination controls
        self.page_info_label.setText(
            f"第 {self._current_page} / {self._total_pages} 页 (共 {self._total_count} 张)"
        )
        self.prev_btn.setEnabled(not batch_busy and self._current_page > 1)
        self.next_btn.setEnabled(
            not batch_busy and self._current_page < self._total_pages
        )
        self.jump_spinbox.setMaximum(self._total_pages)
        self.jump_spinbox.setValue(self._current_page)
        self.jump_spinbox.setEnabled(not batch_busy)
        self.jump_btn.setEnabled(not batch_busy)

        items = db.get_favorites(limit=self._page_size, offset=offset)
        for item_data in items:
            card = WallpaperCard(item_data, self.container)
            card.apply_requested.connect(self.apply_wallpaper_requested.emit)
            card.preview_requested.connect(self._on_preview)
            card.favorite_toggled.connect(self._on_favorite_toggled)
            card.selection_changed.connect(self._on_card_selection_changed)
            card.set_selection_mode(self._batch_selection_mode)
            card.set_selected(wallpaper_download_key(item_data) in self._selected_items)
            card.selection_checkbox.setEnabled(not batch_busy)
            card.fav_btn.setEnabled(not batch_busy)
            self._cards.append(card)

        self._update_batch_controls()
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
        self.refresh()

    def _on_favorite_toggled(self, item: dict[str, Any], is_favorite: bool) -> None:
        if not is_favorite:
            self._selected_items.pop(wallpaper_download_key(item), None)
            self.refresh()

    def _toggle_batch_mode(self) -> None:
        self._set_batch_mode(not self._batch_selection_mode)

    def _set_batch_mode(self, enabled: bool) -> None:
        if self._batch_worker is not None:
            return
        self._batch_selection_mode = enabled
        self.batch_bar.setVisible(enabled)
        self.batch_mode_btn.setText("退出批量" if enabled else "批量下载")
        self.batch_mode_btn.setIcon(
            create_icon("dismiss" if enabled else "download", color="#475569", size=16)
        )
        for card in self._cards:
            card.set_selection_mode(enabled)
        if not enabled:
            self._clear_batch_selection()
        self._update_batch_controls()

    def _on_card_selection_changed(self, item: dict[str, Any], selected: bool) -> None:
        key = wallpaper_download_key(item)
        if selected:
            self._selected_items[key] = dict(item)
        else:
            self._selected_items.pop(key, None)
        self._update_batch_controls()

    def _toggle_select_current_page(self) -> None:
        page_keys = [wallpaper_download_key(card.item_data) for card in self._cards]
        select = bool(page_keys) and not all(
            key in self._selected_items for key in page_keys
        )
        for card, key in zip(self._cards, page_keys, strict=True):
            card.set_selected(select)
            if select:
                self._selected_items[key] = dict(card.item_data)
            else:
                self._selected_items.pop(key, None)
        self._update_batch_controls()

    def _toggle_select_all(self) -> None:
        all_items = db.get_favorites()
        all_by_key = {wallpaper_download_key(item): dict(item) for item in all_items}
        select = bool(all_by_key) and not all(
            key in self._selected_items for key in all_by_key
        )
        self._selected_items = all_by_key if select else {}
        for card in self._cards:
            card.set_selected(
                wallpaper_download_key(card.item_data) in self._selected_items
            )
        self._update_batch_controls()

    def _clear_batch_selection(self) -> None:
        self._selected_items.clear()
        for card in self._cards:
            card.set_selected(False)
        self._update_batch_controls()

    def _update_batch_controls(self) -> None:
        count = len(self._selected_items)
        busy = self._batch_worker is not None
        self.batch_count_label.setText(f"已选择 {count} 张")
        self.download_selected_btn.setText(
            f"下载所选 ({count})" if count else "下载所选"
        )
        self.download_selected_btn.setEnabled(count > 0 and not busy)
        self.clear_selection_btn.setEnabled(count > 0 and not busy)

        page_keys = [wallpaper_download_key(card.item_data) for card in self._cards]
        all_page_selected = bool(page_keys) and all(
            key in self._selected_items for key in page_keys
        )
        self.select_page_btn.setText("取消本页" if all_page_selected else "全选本页")
        self.select_page_btn.setEnabled(bool(page_keys) and not busy)

        all_selected = self._total_count > 0 and count == self._total_count
        self.select_all_btn.setText("取消全选" if all_selected else "全选全部收藏")
        self.select_all_btn.setEnabled(self._total_count > 0 and not busy)

    def _start_batch_download(self) -> None:
        if self._batch_worker is not None or not self._selected_items:
            return
        items = [dict(item) for item in self._selected_items.values()]
        worker = BatchDownloadWorker(items, Path(config.download_dir), self)
        self._batch_worker = worker
        self._batch_result = None
        worker.item_finished.connect(self._on_batch_item_finished)
        worker.batch_completed.connect(self._on_batch_completed)
        worker.finished.connect(lambda w=worker: self._on_batch_thread_finished(w))
        worker.finished.connect(worker.deleteLater)
        self._set_batch_busy(True, len(worker.items))
        worker.start()

    def _set_batch_busy(self, busy: bool, total: int = 0) -> None:
        self.batch_mode_btn.setEnabled(not busy and self._total_count > 0)
        self.random_fav_btn.setEnabled(not busy and self._total_count > 0)
        self.refresh_btn.setEnabled(not busy)
        self.prev_btn.setEnabled(not busy and self._current_page > 1)
        self.next_btn.setEnabled(not busy and self._current_page < self._total_pages)
        self.jump_spinbox.setEnabled(not busy)
        self.jump_btn.setEnabled(not busy)
        self.select_page_btn.setVisible(not busy)
        self.select_all_btn.setVisible(not busy)
        self.clear_selection_btn.setVisible(not busy)
        self.download_selected_btn.setVisible(not busy)
        for card in self._cards:
            card.selection_checkbox.setEnabled(not busy)
            card.fav_btn.setEnabled(not busy)

        self.batch_progress.setVisible(busy)
        self.cancel_download_btn.setVisible(busy)
        self.cancel_download_btn.setEnabled(busy)
        self.cancel_download_btn.setText("取消下载")
        if busy:
            self.batch_progress.setRange(0, max(1, total))
            self.batch_progress.setValue(0)
        self._update_batch_controls()

    def _on_batch_item_finished(self, processed: int, total: int, title: str) -> None:
        self.batch_progress.setMaximum(max(1, total))
        self.batch_progress.setValue(processed)
        self.batch_count_label.setText(f"正在下载 {processed} / {total}：{title}")

    def _cancel_batch_download(self) -> None:
        if self._batch_worker is None:
            return
        self._batch_worker.requestInterruption()
        self.cancel_download_btn.setEnabled(False)
        self.cancel_download_btn.setText("正在取消...")

    def _on_batch_completed(
        self, downloaded: int, skipped: int, failed: int, cancelled: bool
    ) -> None:
        self._batch_result = (downloaded, skipped, failed, cancelled)

    def _on_batch_thread_finished(self, worker: BatchDownloadWorker) -> None:
        if worker is not self._batch_worker:
            return
        result = self._batch_result or (0, 0, len(worker.items), False)
        self._batch_worker = None
        self._set_batch_busy(False)
        self._set_batch_mode(False)
        show_batch_download_result(self, Path(config.download_dir), *result)

    def _apply_random_favorite(self) -> None:
        fav = db.get_random_favorite()
        if fav:
            self.apply_wallpaper_requested.emit(fav)
        else:
            show_info(self, "提示", "收藏夹为空，无法设置壁纸")

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
