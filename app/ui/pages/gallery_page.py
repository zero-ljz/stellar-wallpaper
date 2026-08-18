"""Polished gallery page for browsing 360 categories and searching wallpapers."""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...constants import CATEGORIES, CATEGORY_MAP
from ...core.api_client import api_client
from ..components.category_tab_bar import CATEGORY_EMOJIS, CategoryTabBar
from ..components.preview_dialog import PreviewDialog
from ..components.wallpaper_card import WallpaperCard


class FetchPageWorker(QThread):
    data_loaded = Signal(dict, int)  # data, req_id
    error = Signal(str, int)         # error_msg, req_id

    def __init__(
        self,
        req_id: int,
        category_id: str = "",
        keyword: str = "",
        start: int = 0,
        count: int = 24,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.req_id = req_id
        self.category_id = category_id
        self.keyword = keyword
        self.start_idx = start
        self.count = count

    def run(self) -> None:
        try:
            if self.keyword:
                result = api_client.search_wallpapers(self.keyword, self.start_idx, self.count)
            else:
                result = api_client.get_category_wallpapers(self.category_id or "36", self.start_idx, self.count)
            self.data_loaded.emit(result, self.req_id)
        except Exception as e:
            self.error.emit(str(e), self.req_id)


class GalleryPage(QWidget):
    """Browse wallpapers by official categories or keyword search with modern responsive layout."""

    apply_wallpaper_requested = Signal(dict)

    def __init__(self, parent: QWidget | None = None, auto_load: bool = True) -> None:
        super().__init__(parent)
        self._current_cat_id = "36"  # default 4K专区
        self._current_keyword = ""
        self._page_size = 24
        self._current_page = 1
        self._total_count = 0
        self._total_pages = 1
        self._req_id = 0
        self._active_workers: set[FetchPageWorker] = set()

        self._cards: list[WallpaperCard] = []
        self._current_cols = 0

        self._init_ui()
        if auto_load:
            self.load_page(1)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # 1. Top Modern Fluent 2 Category Tab Bar
        self.cat_tab_bar = CategoryTabBar(
            categories=CATEGORIES,
            default_cat_id=self._current_cat_id,
            parent=self,
        )
        self.cat_tab_bar.category_selected.connect(self._on_category_selected)
        layout.addWidget(self.cat_tab_bar)

        # 2. Control Bar: Category Info Header + Search Controls
        control_bar = QHBoxLayout()
        control_bar.setSpacing(12)

        # Left Info Section: Category Title, Desc & Count Badge
        self.header_info_widget = QWidget(self)
        info_layout = QHBoxLayout(self.header_info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10)

        initial_cat = next((c for c in CATEGORIES if c["id"] == self._current_cat_id), CATEGORIES[0])
        initial_emoji = CATEGORY_EMOJIS.get(self._current_cat_id, "✨")

        self.header_title_lbl = QLabel(f"{initial_emoji} {initial_cat['name']}", self.header_info_widget)
        font = self.header_title_lbl.font()
        font.setPointSize(14)
        font.setBold(True)
        self.header_title_lbl.setFont(font)
        info_layout.addWidget(self.header_title_lbl)

        self.header_desc_lbl = QLabel(initial_cat.get("desc", ""), self.header_info_widget)
        self.header_desc_lbl.setStyleSheet("color: #475569; font-weight: 500; font-size: 12px;")
        info_layout.addWidget(self.header_desc_lbl)

        self.header_count_badge = QLabel("共 0 张", self.header_info_widget)
        self.header_count_badge.setStyleSheet("""
            background-color: #EFF6FF;
            color: #0078D4;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 10px;
            border: 1px solid #BFDBFE;
        """)
        info_layout.addWidget(self.header_count_badge)
        control_bar.addWidget(self.header_info_widget)

        # Active Search Tag Widget (Hidden by default, shown when searching)
        self.search_tag_widget = QWidget(self)
        search_tag_layout = QHBoxLayout(self.search_tag_widget)
        search_tag_layout.setContentsMargins(0, 0, 0, 0)
        search_tag_layout.setSpacing(8)

        self.search_tag_lbl = QLabel("", self.search_tag_widget)
        self.search_tag_lbl.setStyleSheet("""
            background-color: #FEF3C7;
            color: #92400E;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 8px;
            border: 1px solid #FDE68A;
        """)
        search_tag_layout.addWidget(self.search_tag_lbl)

        self.back_to_cat_btn = QPushButton("✕ 返回分类", self.search_tag_widget)
        self.back_to_cat_btn.setFixedHeight(28)
        self.back_to_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_to_cat_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 12px;
                padding: 2px 10px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #0F172A;
            }
        """)
        self.back_to_cat_btn.clicked.connect(self._on_reset_search)
        search_tag_layout.addWidget(self.back_to_cat_btn)

        control_bar.addWidget(self.search_tag_widget)
        self.search_tag_widget.hide()

        control_bar.addStretch()

        # Right Search Box & Actions
        self.search_input = QLineEdit(self)
        self.search_input.setFixedWidth(280)
        self.search_input.setFixedHeight(34)
        self.search_input.setPlaceholderText("🔍 搜索壁纸（星空/动漫/赛博朋克）...")
        self.search_input.returnPressed.connect(self._on_search)
        control_bar.addWidget(self.search_input)

        self.search_btn = QPushButton("搜索", self)
        self.search_btn.setProperty("class", "PrimaryButton")
        self.search_btn.setFixedHeight(34)
        self.search_btn.clicked.connect(self._on_search)
        control_bar.addWidget(self.search_btn)

        self.refresh_btn = QPushButton("🔄 刷新", self)
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.clicked.connect(lambda: self.load_page(self._current_page))
        control_bar.addWidget(self.refresh_btn)

        layout.addLayout(control_bar)

        # 3. Wallpapers Responsive Grid View
        self.grid_scroll = QScrollArea(self)
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.grid_scroll.setStyleSheet("background: transparent; border: none;")
        self.grid_scroll.viewport().setStyleSheet("background: transparent; border: none;")
        self.grid_container = QWidget(self.grid_scroll)
        self.grid_container.setStyleSheet("background: transparent; border: none;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 4, 0, 4)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.grid_scroll.setWidget(self.grid_container)
        layout.addWidget(self.grid_scroll, 1)

        # Loading / Status label
        self.status_label = QLabel("正在加载壁纸...", self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #64748B; font-size: 14px; padding: 40px;")
        layout.addWidget(self.status_label)
        self.status_label.hide()

        # 4. Bottom Modern Pagination Bar
        page_bar = QHBoxLayout()
        page_bar.setContentsMargins(4, 4, 4, 4)
        page_bar.setSpacing(10)
        page_bar.addStretch()

        self.prev_btn = QPushButton("⬅ 上一页", self)
        self.prev_btn.clicked.connect(self._prev_page)
        page_bar.addWidget(self.prev_btn)

        self.page_info_label = QLabel("第 1 / 1 页 (共 0 张)", self)
        self.page_info_label.setStyleSheet("color: #334155; font-weight: 600; font-size: 12px;")
        page_bar.addWidget(self.page_info_label)

        self.next_btn = QPushButton("下一页 ➡", self)
        self.next_btn.clicked.connect(self._next_page)
        page_bar.addWidget(self.next_btn)

        page_bar.addSpacing(16)

        jump_lbl = QLabel("跳至", self)
        jump_lbl.setStyleSheet("color: #334155; font-weight: 600; font-size: 12px;")
        page_bar.addWidget(jump_lbl)

        self.jump_spinbox = QSpinBox(self)
        self.jump_spinbox.setMinimum(1)
        self.jump_spinbox.setMaximum(1)
        self.jump_spinbox.setValue(1)
        self.jump_spinbox.setFixedWidth(72)
        self.jump_spinbox.setFixedHeight(34)
        page_bar.addWidget(self.jump_spinbox)

        self.jump_btn = QPushButton("跳转", self)
        self.jump_btn.setFixedHeight(34)
        self.jump_btn.clicked.connect(self._jump_page)
        page_bar.addWidget(self.jump_btn)

        page_bar.addStretch()
        layout.addLayout(page_bar)

    def _calculate_cols(self) -> int:
        """Calculate optimal column count dynamically based on viewport width."""
        vp_width = self.grid_scroll.viewport().width()
        scroll_w = self.grid_scroll.width()
        page_w = self.width() - 48

        width = vp_width if (vp_width > 50 and abs(vp_width - scroll_w) <= 30) else max(scroll_w, page_w, 300)
        card_total_width = 264 + 16  # 264px card width + 16px grid horizontal spacing
        cols = max(2, (width + 16) // card_total_width)
        return cols

    def _relayout_grid(self, force: bool = False) -> None:
        """Dynamically reposition cards in grid without re-rendering or refetching."""
        if not self._cards:
            return
        cols = self._calculate_cols()
        if not force and cols == self._current_cols:
            return
        self._current_cols = cols

        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

        for index, card in enumerate(self._cards):
            row = index // cols
            col = index % cols
            self.grid_layout.addWidget(card, row, col)

    def _on_category_selected(self, cat_id: str, cat_name: str = "", cat_desc: str = "") -> None:
        self._current_cat_id = cat_id
        self._current_keyword = ""
        self.search_input.clear()

        # Update header info
        emoji = CATEGORY_EMOJIS.get(cat_id, "🖼️")
        name = cat_name or CATEGORY_MAP.get(cat_id, "壁纸")
        self.header_title_lbl.setText(f"{emoji} {name}")
        self.header_desc_lbl.setText(cat_desc)

        self.search_tag_widget.hide()
        self.header_info_widget.show()

        self.load_page(1)

    def _on_search(self) -> None:
        kw = self.search_input.text().strip()
        if not kw:
            return
        self._current_keyword = kw

        # Update UI to search mode
        self.cat_tab_bar.clear_selection()
        self.header_info_widget.hide()
        self.search_tag_lbl.setText(f"🔍 搜索关键词:  \"{kw}\"")
        self.search_tag_widget.show()

        self.load_page(1)

    def _on_reset_search(self) -> None:
        self.search_input.clear()
        self._current_keyword = ""
        self.cat_tab_bar.select_category(self._current_cat_id)

    def load_page(self, page_num: int) -> None:
        self._current_page = max(1, page_num)
        start = (self._current_page - 1) * self._page_size
        self._req_id += 1
        req_id = self._req_id

        self._clear_grid()
        self.status_label.setText("正在努力加载壁纸...")
        self.status_label.show()

        worker = FetchPageWorker(
            req_id=req_id,
            category_id=self._current_cat_id,
            keyword=self._current_keyword,
            start=start,
            count=self._page_size,
            parent=self,
        )
        self._active_workers.add(worker)

        def _on_loaded(data: dict[str, Any], r_id: int, w=worker) -> None:
            self._active_workers.discard(w)
            if r_id == self._req_id:
                self._on_page_loaded(data)

        def _on_err(err: str, r_id: int, w=worker) -> None:
            self._active_workers.discard(w)
            if r_id == self._req_id:
                self._on_page_error(err)

        worker.data_loaded.connect(_on_loaded)
        worker.error.connect(_on_err)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _clear_grid(self) -> None:
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._current_cols = 0

    def _on_page_loaded(self, data: dict[str, Any]) -> None:
        self.status_label.hide()
        if data.get("error"):
            self._on_page_error(data["error"])
            return

        items = data.get("items", [])
        self._total_count = data.get("total", len(items))
        self._total_pages = max(1, math.ceil(self._total_count / self._page_size))

        self.page_info_label.setText(
            f"第 {self._current_page} / {self._total_pages} 页 (共 {self._total_count} 张)"
        )
        self.header_count_badge.setText(f"共 {self._total_count} 张")

        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)
        self.jump_spinbox.setMaximum(self._total_pages)
        self.jump_spinbox.setValue(self._current_page)

        if not items:
            self.status_label.setText("未找到相关壁纸，换个分类或关键词试试吧~")
            self.status_label.show()
            return

        self._cards = []
        for item_data in items:
            card = WallpaperCard(item_data, self.grid_container)
            card.apply_requested.connect(self._on_card_apply)
            card.preview_requested.connect(self._on_card_preview)
            self._cards.append(card)

        self._relayout_grid(force=True)

    def _on_page_error(self, err: str) -> None:
        self.status_label.setText(f"加载失败: {err}")
        self.status_label.show()

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

    def _on_card_apply(self, item_data: dict[str, Any]) -> None:
        self.apply_wallpaper_requested.emit(item_data)

    def _on_card_preview(self, item_data: dict[str, Any]) -> None:
        dialog = PreviewDialog(item_data, self)
        dialog.apply_requested.connect(self.apply_wallpaper_requested.emit)
        dialog.exec()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout_grid()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._relayout_grid()
