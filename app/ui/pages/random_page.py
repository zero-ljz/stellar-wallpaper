"""Polished random wallpaper switcher page with interactive category chips and desktop preview."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...config import config
from ...constants import CATEGORIES, CATEGORY_MAP
from ...core.database import db
from ...core.scheduler import scheduler
from ..components.message_box import show_info, show_success, show_warning
from ..components.wallpaper_card import extract_item_ids as _extract_item_ids
from ..icons import create_fluent_icon, create_icon

# Microsoft Fluent Category Vector Icons
CATEGORY_ICONS = {
    "latest": "cat_latest",
    "bing": "cat_bing",
    "picsum": "cat_picsum",
    "36": "cat_4k",
    "9": "cat_landscape",
    "26": "cat_anime",
    "5": "cat_game",
    "12": "cat_car",
    "14": "cat_pet",
    "6": "cat_beauty",
    "10": "cat_fashion",
    "15": "cat_fresh",
    "7": "cat_movie",
    "30": "cat_love",
    "11": "cat_star",
    "22": "cat_military",
    "16": "cat_sports",
    "35": "cat_text",
}


class CategoryChipButton(QPushButton):
    """Modern interactive toggle chip for category selection with Fluent vector icons."""

    def __init__(self, cat_id: str, cat_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cat_id = cat_id
        self.cat_name = cat_name
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self._update_style()
        self.toggled.connect(self._on_toggled)

    def _update_style(self) -> None:
        icon_key = CATEGORY_ICONS.get(self.cat_id, "gallery")
        is_checked = self.isChecked()
        color = "#0078D4" if is_checked else "#475569"
        self.setIcon(create_fluent_icon(icon_key, color=color, size=16))
        self.setIconSize(QSize(16, 16))
        self.setText(f" {self.cat_name}")

        if is_checked:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #EFF6FF;
                    border: 1.5px solid #0078D4;
                    border-radius: 8px;
                    color: #0067B8;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 0 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #DBEAFE;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                    color: #1E293B;
                    font-weight: normal;
                    font-size: 13px;
                    padding: 0 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    border-color: #93C5FD;
                    background-color: #F8FAFC;
                    color: #0B0F19;
                }
            """)

    def _on_toggled(self, _checked: bool) -> None:
        self._update_style()


class RandomSwitcherPage(QWidget):
    """Multi-category pool random wallpaper switcher page with polished UI."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._category_chips: dict[str, CategoryChipButton] = {}
        self._current_wallpaper: dict[str, Any] | None = config.last_wallpaper
        self._init_ui()
        self._load_config_categories()

        # Connect to scheduler signals for live progress feedback
        scheduler.stage_changed.connect(self._on_stage_changed)
        scheduler.download_progress.connect(self._on_download_progress)
        scheduler.wallpaper_applied.connect(self._on_wallpaper_applied)
        scheduler.error_occurred.connect(self._on_switch_error)

        if self._current_wallpaper:
            self._update_current_display(self._current_wallpaper)

    def _init_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        
        container = QWidget(scroll)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(28, 20, 28, 20)
        main_layout.setSpacing(16)

        # 1. Top Hero Switcher Card
        hero_card = QFrame(container)
        hero_card.setObjectName("RandomHeroCard")
        hero_card.setStyleSheet("""
            QFrame#RandomHeroCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(12)

        hero_top = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title_lbl = QLabel("多分类混合随机换壁纸", hero_card)
        font = title_lbl.font()
        font.setPointSize(16)
        font.setBold(True)
        title_lbl.setFont(font)
        title_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        title_box.addWidget(title_lbl)

        self.summary_lbl = QLabel("在下方勾选您喜欢的多个分类，点击右侧按钮即可从分类池中随机抽选并应用", hero_card)
        self.summary_lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 12px; border: none; background: transparent;")
        title_box.addWidget(self.summary_lbl)
        hero_top.addLayout(title_box)

        hero_top.addStretch()

        self.switch_btn = QPushButton("立即随机换壁纸", hero_card)
        self.switch_btn.setIcon(create_icon("shuffle", color="#FFFFFF", size=18))
        self.switch_btn.setProperty("class", "PrimaryButton")
        self.switch_btn.setFixedHeight(42)
        font = self.switch_btn.font()
        font.setPointSize(13)
        font.setBold(True)
        self.switch_btn.setFont(font)
        self.switch_btn.clicked.connect(self._trigger_random_switch)
        hero_top.addWidget(self.switch_btn)

        hero_layout.addLayout(hero_top)

        # Progress row
        self.prog_box = QWidget(hero_card)
        self.prog_box.setStyleSheet("border: none; background: transparent;")
        prog_vbox = QVBoxLayout(self.prog_box)
        prog_vbox.setContentsMargins(0, 4, 0, 0)
        prog_vbox.setSpacing(4)

        prog_txt_row = QHBoxLayout()
        self.prog_stage_lbl = QLabel("就绪 - 随时点击「立即随机换壁纸」", self.prog_box)
        self.prog_stage_lbl.setStyleSheet("color: #0B0F19; font-weight: 600; font-size: 12px; border: none; background: transparent;")
        prog_txt_row.addWidget(self.prog_stage_lbl)

        prog_txt_row.addStretch()
        self.prog_pct_lbl = QLabel("", self.prog_box)
        self.prog_pct_lbl.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 12px; border: none; background: transparent;")
        prog_txt_row.addWidget(self.prog_pct_lbl)
        prog_vbox.addLayout(prog_txt_row)

        self.progress_bar = QProgressBar(self.prog_box)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        prog_vbox.addWidget(self.progress_bar)

        hero_layout.addWidget(self.prog_box)
        main_layout.addWidget(hero_card)

        # 2. Category Pool Selector Card
        cat_card = QFrame(container)
        cat_card.setObjectName("RandomCatCard")
        cat_card.setStyleSheet("""
            QFrame#RandomCatCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        cat_vbox = QVBoxLayout(cat_card)
        cat_vbox.setContentsMargins(20, 16, 20, 18)
        cat_vbox.setSpacing(14)

        # Category Header with quick select tools
        cat_hdr = QHBoxLayout()
        cat_title = QLabel("随机抽选分类池", cat_card)
        font = cat_title.font()
        font.setBold(True)
        font.setPointSize(14)
        cat_title.setFont(font)
        cat_title.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        cat_hdr.addWidget(cat_title)

        self.pool_count_badge = QLabel(f"已选 {len(CATEGORIES)} 个分类", cat_card)
        self.pool_count_badge.setStyleSheet("""
            background-color: #EFF6FF;
            color: #0078D4;
            font-weight: 600;
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 10px;
            border: none;
        """)
        cat_hdr.addWidget(self.pool_count_badge)

        cat_hdr.addStretch()

        self.select_all_btn = QPushButton("全选", cat_card)
        self.select_all_btn.setIcon(create_icon("check", color="#475569", size=14))
        self.select_all_btn.clicked.connect(self._select_all_categories)
        cat_hdr.addWidget(self.select_all_btn)

        self.clear_all_btn = QPushButton("清空", cat_card)
        self.clear_all_btn.setIcon(create_icon("close", color="#475569", size=14))
        self.clear_all_btn.clicked.connect(self._clear_all_categories)
        cat_hdr.addWidget(self.clear_all_btn)

        self.recommend_btn = QPushButton("精选组合 (4K+必应+Picsum+风景)", cat_card)
        self.recommend_btn.setIcon(create_icon("sparkle", color="#475569", size=14))
        self.recommend_btn.clicked.connect(self._select_recommended_categories)
        cat_hdr.addWidget(self.recommend_btn)

        cat_vbox.addLayout(cat_hdr)

        # Grid of Category Chip buttons (3 columns)
        cat_grid = QGridLayout()
        cat_grid.setSpacing(10)

        cols = 3
        for idx, cat in enumerate(CATEGORIES):
            r = idx // cols
            c = idx % cols
            cid = cat["id"]
            chip = CategoryChipButton(cid, cat["name"], cat_card)
            chip.toggled.connect(self._on_category_toggled)
            self._category_chips[cid] = chip
            cat_grid.addWidget(chip, r, c)

        cat_vbox.addLayout(cat_grid)
        main_layout.addWidget(cat_card)

        # 3. Current Desktop Wallpaper Display Card
        cur_card = QFrame(container)
        cur_card.setObjectName("RandomCurCard")
        cur_card.setStyleSheet("""
            QFrame#RandomCurCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        cur_layout = QHBoxLayout(cur_card)
        cur_layout.setContentsMargins(20, 16, 20, 16)
        cur_layout.setSpacing(20)

        # Image preview frame (16:9 widescreen mockup)
        self.preview_image_lbl = QLabel(cur_card)
        self.preview_image_lbl.setFixedSize(260, 146)
        self.preview_image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_lbl.setStyleSheet("""
            background-color: #1E293B;
            border-radius: 8px;
            border: none;
            color: #94A3B8;
            font-size: 12px;
        """)
        self.preview_image_lbl.setText("暂无壁纸信息")
        cur_layout.addWidget(self.preview_image_lbl)

        # Information and Action column
        cur_info_box = QVBoxLayout()
        cur_info_box.setSpacing(8)

        self.cur_title_lbl = QLabel("当前桌面壁纸", cur_card)
        font = self.cur_title_lbl.font()
        font.setBold(True)
        font.setPointSize(14)
        self.cur_title_lbl.setFont(font)
        self.cur_title_lbl.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        cur_info_box.addWidget(self.cur_title_lbl)

        self.cur_meta_lbl = QLabel("分类专区: 4K专区  |  分辨率: 3840×2160", cur_card)
        self.cur_meta_lbl.setStyleSheet("color: #334155; font-weight: 600; font-size: 12px; border: none; background: transparent;")
        cur_info_box.addWidget(self.cur_meta_lbl)

        self.cur_time_lbl = QLabel("更换时间: 刚刚", cur_card)
        self.cur_time_lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 11px; border: none; background: transparent;")
        cur_info_box.addWidget(self.cur_time_lbl)

        cur_info_box.addStretch()

        # Action tools row
        tools_row = QHBoxLayout()
        tools_row.setSpacing(8)

        self.fav_btn = QPushButton("收藏当前壁纸", cur_card)
        self.fav_btn.setIcon(create_icon("star", color="#475569", size=16))
        self.fav_btn.clicked.connect(self._toggle_current_favorite)
        tools_row.addWidget(self.fav_btn)

        self.save_btn = QPushButton("保存原图", cur_card)
        self.save_btn.setIcon(create_icon("download", color="#475569", size=16))
        self.save_btn.clicked.connect(self._save_current_wallpaper)
        tools_row.addWidget(self.save_btn)

        self.open_loc_btn = QPushButton("打开所在目录", cur_card)
        self.open_loc_btn.setIcon(create_icon("folder", color="#475569", size=16))
        self.open_loc_btn.clicked.connect(self._open_current_location)
        tools_row.addWidget(self.open_loc_btn)

        tools_row.addStretch()
        cur_info_box.addLayout(tools_row)

        cur_layout.addLayout(cur_info_box, 1)
        main_layout.addWidget(cur_card)
        main_layout.addStretch()

        scroll.setWidget(container)
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _load_config_categories(self) -> None:
        selected = set(config.selected_categories)
        for cid, chip in self._category_chips.items():
            chip.blockSignals(True)
            chip.setChecked(cid in selected)
            chip._update_style()
            chip.blockSignals(False)
        self._update_pool_count_badge()

    def _on_category_toggled(self) -> None:
        selected = [cid for cid, chip in self._category_chips.items() if chip.isChecked()]
        if not selected:
            if "36" in self._category_chips:
                self._category_chips["36"].setChecked(True)
                selected = ["36"]
        config.selected_categories = selected
        self._update_pool_count_badge()

    def _update_pool_count_badge(self) -> None:
        count = len(config.selected_categories)
        self.pool_count_badge.setText(f"已选 {count} 个分类")

    def _select_all_categories(self) -> None:
        for chip in self._category_chips.values():
            chip.setChecked(True)

    def _clear_all_categories(self) -> None:
        for chip in self._category_chips.values():
            chip.setChecked(False)
        if "36" in self._category_chips:
            self._category_chips["36"].setChecked(True)

    def _select_recommended_categories(self) -> None:
        recommended = {"36", "bing", "picsum", "9", "26"}  # 4K, Bing, Picsum, Landscape, Anime
        for cid, chip in self._category_chips.items():
            chip.setChecked(cid in recommended)

    def _trigger_random_switch(self) -> None:
        selected = [cid for cid, chip in self._category_chips.items() if chip.isChecked()]
        self.switch_btn.setEnabled(False)
        self.switch_btn.setText("正在切换...")
        self.progress_bar.setValue(10)
        self.prog_stage_lbl.setText("正在连接服务器获取壁纸...")
        scheduler.trigger_switch(source="categories", category_ids=selected)

    def _on_stage_changed(self, stage: str) -> None:
        self.prog_stage_lbl.setText(stage)

    def _on_download_progress(self, current: int, total: int, percent: int) -> None:
        self.progress_bar.setValue(percent)
        cur_mb = current / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        if total > 0:
            self.prog_pct_lbl.setText(f"{percent}% ({cur_mb:.1f}MB / {tot_mb:.1f}MB)")
        else:
            self.prog_pct_lbl.setText(f"{cur_mb:.1f} MB")

    def _on_wallpaper_applied(self, item: dict[str, Any]) -> None:
        self.switch_btn.setEnabled(True)
        self.switch_btn.setText("立即随机换壁纸")
        self.switch_btn.setIcon(create_icon("shuffle", color="#FFFFFF", size=18))
        self.progress_bar.setValue(100)
        self.prog_stage_lbl.setText("壁纸更换成功！")
        self.prog_pct_lbl.setText("100%")
        self._current_wallpaper = item
        self._update_current_display(item)

    def _on_switch_error(self, err: str) -> None:
        self.switch_btn.setEnabled(True)
        self.switch_btn.setText("立即随机换壁纸")
        self.switch_btn.setIcon(create_icon("shuffle", color="#FFFFFF", size=18))
        self.prog_stage_lbl.setText(f"更换失败: {err}")
        self.prog_pct_lbl.setText("")

    def _update_current_display(self, item: dict[str, Any]) -> None:
        raw_title = item.get("title") or item.get("tag") or "桌面壁纸"
        title = raw_title.replace("_360Wallpaper_", "").replace("_category_", "").replace("_", " ").strip() or "桌面壁纸"
        cat_name = item.get("category_name") or CATEGORY_MAP.get(str(item.get("category_id", "")), "推荐")
        res = item.get("resolution") or "超高清"
        time_str = item.get("applied_at") or "刚刚"

        self.cur_title_lbl.setText(title)
        self.cur_meta_lbl.setText(f"分类专区: {cat_name}  |  分辨率: {res}")
        self.cur_time_lbl.setText(f"更换时间: {time_str}")

        local_path = item.get("local_path")
        if local_path and Path(local_path).exists():
            pix = QPixmap(local_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    self.preview_image_lbl.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.preview_image_lbl.setPixmap(scaled)

        # Update fav button
        wid, url = _extract_item_ids(item)
        is_fav = db.is_favorite(wid, url)
        self.fav_btn.setText("取消收藏" if is_fav else "收藏当前壁纸")
        self.fav_btn.setIcon(
            create_icon("star_filled" if is_fav else "star", color="#F59E0B" if is_fav else "#475569", size=16)
        )

    def _toggle_current_favorite(self) -> None:
        if not self._current_wallpaper:
            return
        wid, url = _extract_item_ids(self._current_wallpaper)
        if db.is_favorite(wid, url):
            db.remove_favorite(wid, url)
            self.fav_btn.setText("收藏当前壁纸")
            self.fav_btn.setIcon(create_icon("star", color="#475569", size=16))
        else:
            db.add_favorite(self._current_wallpaper)
            self.fav_btn.setText("取消收藏")
            self.fav_btn.setIcon(create_icon("star_filled", color="#F59E0B", size=16))

    def _save_current_wallpaper(self) -> None:
        if not self._current_wallpaper:
            return
        local = self._current_wallpaper.get("local_path")
        if not local or not Path(local).exists():
            show_warning(self, "提示", "未找到本地壁纸文件")
            return

        save_dir = Path(config.download_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        target = save_dir / f"Saved_{Path(local).name}"

        import shutil
        shutil.copy2(local, target)
        show_success(self, "保存成功", f"壁纸已成功保存到:\n{target}")

    def _open_current_location(self) -> None:
        if not self._current_wallpaper:
            return
        local = self._current_wallpaper.get("local_path")
        if local and Path(local).exists():
            if os.name == "nt":
                os.system(f'explorer /select,"{local}"')
        else:
            if os.name == "nt":
                os.startfile(config.download_dir)
