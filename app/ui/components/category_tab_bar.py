"""Polished horizontal Category Tab Bar component with wheel scrolling and navigation arrows."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QPoint, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from ...constants import CATEGORIES

# Rich Category Emojis / Badges for visual appeal
CATEGORY_EMOJIS = {
    "36": "✨",  # 4K专区
    "9": "🏔️",  # 风景大片
    "26": "🎨",  # 动漫卡通
    "5": "🎮",  # 游戏壁纸
    "12": "🏎️",  # 汽车天下
    "14": "🐱",  # 萌宠动物
    "6": "💃",  # 美女模特
    "10": "🕶️",  # 炫酷时尚
    "15": "🍃",  # 小清新
    "7": "🎬",  # 影视剧照
    "30": "💖",  # 爱情美图
    "11": "🌟",  # 明星风尚
    "22": "🚀",  # 军事天地
    "16": "⚽",  # 劲爆体育
    "35": "✍️",  # 文字控
}


class CategoryTabButton(QPushButton):
    """Clean minimalist tab button with bottom indicator bar (no clunky background)."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-bottom: 2.5px solid transparent;
                border-radius: 0px;
                padding: 4px 12px;
                font-size: 13px;
                font-weight: 650;
                color: #334155;
            }
            QPushButton:hover {
                color: #0B0F19;
                border-bottom: 2.5px solid #94A3B8;
            }
            QPushButton:checked {
                color: #0078D4;
                font-weight: 800;
                border-bottom: 2.5px solid #0078D4;
            }
        """)


class CategoryNavArrowButton(QPushButton):
    """Clean compact scroll arrow button."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setFixedSize(24, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                color: #94A3B8;
                padding: 0;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
                color: #0F172A;
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton:disabled {
                color: transparent;
                background-color: transparent;
            }
        """)


class SmoothHorizontalScrollArea(QScrollArea):
    """Horizontal scroll area that responds to normal vertical mouse wheel scrolling."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: transparent; border: none;")

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        """Convert vertical mouse wheel scrolling into horizontal scrolling."""
        delta = event.angleDelta().y()
        if delta == 0:
            delta = event.angleDelta().x()
        if delta != 0:
            h_bar = self.horizontalScrollBar()
            step = -int(delta * 0.8)
            h_bar.setValue(h_bar.value() + step)
            event.accept()
        else:
            super().wheelEvent(event)


class CategoryTabBar(QFrame):
    """Modern Clean Horizontal Category Tab Navigation Bar.

    Features:
    - Pure transparent floating tabs with bottom accent indicator
    - Mouse wheel horizontal scrolling
    - Smooth arrow buttons with auto-fade
    - Auto-scrolling to center selected tab
    - Seamless category switching signal
    """

    category_selected = Signal(str, str, str)  # cat_id, cat_name, cat_desc

    def __init__(
        self,
        categories: list[dict[str, str]] | None = None,
        default_cat_id: str = "36",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("CategoryTabBarContainer")
        self._categories = categories or CATEGORIES
        self._current_cat_id = default_cat_id
        self._buttons: dict[str, CategoryTabButton] = {}

        self._init_ui()

    def _init_ui(self) -> None:
        self.setFixedHeight(38)
        self.setStyleSheet("""
            QFrame#CategoryTabBarContainer {
                background: transparent;
                border: none;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Left scroll arrow button
        self.left_arrow_btn = CategoryNavArrowButton("‹", self)
        self.left_arrow_btn.clicked.connect(self._scroll_left)
        main_layout.addWidget(self.left_arrow_btn)

        # Scroll Area
        self.scroll_area = SmoothHorizontalScrollArea(self)
        self.scroll_container = QWidget(self.scroll_area)
        self.scroll_container.setStyleSheet("background: transparent; border: none;")
        self.tabs_layout = QHBoxLayout(self.scroll_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(4)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        for cat in self._categories:
            cid = cat["id"]
            name = cat["name"]
            desc = cat.get("desc", "")
            emoji = CATEGORY_EMOJIS.get(cid, "🖼️")

            btn = CategoryTabButton(f"{emoji}  {name}", self.scroll_container)
            btn.setToolTip(f"{name}\n{desc}" if desc else name)

            if cid == self._current_cat_id:
                btn.setChecked(True)

            self.btn_group.addButton(btn)
            self._buttons[cid] = btn
            self.tabs_layout.addWidget(btn)

            btn.clicked.connect(
                lambda _c=False, target_id=cid, target_name=name, target_desc=desc: self._on_btn_clicked(
                    target_id, target_name, target_desc
                )
            )

        self.tabs_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Right scroll arrow button
        self.right_arrow_btn = CategoryNavArrowButton("›", self)
        self.right_arrow_btn.clicked.connect(self._scroll_right)
        main_layout.addWidget(self.right_arrow_btn)

        # Monitor scroll bar range and position
        h_bar = self.scroll_area.horizontalScrollBar()
        h_bar.rangeChanged.connect(self._update_arrow_states)
        h_bar.valueChanged.connect(self._update_arrow_states)
        self._update_arrow_states()

    def _on_btn_clicked(self, cat_id: str, cat_name: str, cat_desc: str) -> None:
        self._current_cat_id = cat_id
        self._scroll_to_button(self._buttons.get(cat_id))
        self.category_selected.emit(cat_id, cat_name, cat_desc)

    def _scroll_to_button(self, btn: CategoryTabButton | None) -> None:
        if not btn:
            return
        h_bar = self.scroll_area.horizontalScrollBar()
        btn_center_x = btn.geometry().center().x()
        viewport_width = self.scroll_area.viewport().width()
        target_value = btn_center_x - (viewport_width // 2)
        h_bar.setValue(max(0, min(target_value, h_bar.maximum())))

    def _scroll_left(self) -> None:
        h_bar = self.scroll_area.horizontalScrollBar()
        h_bar.setValue(max(0, h_bar.value() - 240))

    def _scroll_right(self) -> None:
        h_bar = self.scroll_area.horizontalScrollBar()
        h_bar.setValue(min(h_bar.maximum(), h_bar.value() + 240))

    def _update_arrow_states(self) -> None:
        h_bar = self.scroll_area.horizontalScrollBar()
        can_scroll = h_bar.maximum() > 0
        if not can_scroll:
            self.left_arrow_btn.setEnabled(False)
            self.right_arrow_btn.setEnabled(False)
            return
        self.left_arrow_btn.setEnabled(h_bar.value() > 0)
        self.right_arrow_btn.setEnabled(h_bar.value() < h_bar.maximum())

    def select_category(self, cat_id: str) -> None:
        """Programmatically select a category."""
        if cat_id in self._buttons:
            btn = self._buttons[cat_id]
            btn.setChecked(True)
            self._current_cat_id = cat_id
            self._scroll_to_button(btn)
            cat_data = next((c for c in self._categories if c["id"] == cat_id), None)
            if cat_data:
                self.category_selected.emit(cat_id, cat_data["name"], cat_data.get("desc", ""))

    def clear_selection(self) -> None:
        """Clear checked state for all category buttons (e.g. when searching)."""
        self.btn_group.setExclusive(False)
        for btn in self._buttons.values():
            btn.setChecked(False)
        self.btn_group.setExclusive(True)

    def get_current_category_id(self) -> str:
        return self._current_cat_id

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_arrow_states()
