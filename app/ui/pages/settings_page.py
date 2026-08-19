"""Polished settings page following Windows 11 Settings design aesthetics with modern switches."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...config import config
from ...constants import APP_NAME, APP_VERSION, WALLPAPER_STYLES
from ...core.cache_manager import cache_mgr
from ...core.wallpaper_setter import wallpaper_setter
from ..components.message_box import show_info, show_question, show_success
from ..components.switch_toggle import SwitchToggle
from ..icons import create_fluent_pixmap, create_icon


class StyleOptionCard(QPushButton):
    """Visual style choice card for wallpaper presentation."""

    def __init__(self, key: str, name: str, desc: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.key = key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(54)
        self.setText(f"{name}\n{desc}")
        self.toggled.connect(self._on_toggled)
        self._update_style()

    def _update_style(self) -> None:
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton {
                    background-color: #EFF6FF;
                    border: 1.5px solid #0078D4;
                    border-radius: 8px;
                    color: #0078D4;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 6px 14px;
                    text-align: left;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                    color: #334155;
                    font-size: 12px;
                    padding: 6px 14px;
                    text-align: left;
                }
                QPushButton:hover {
                    border-color: #CBD5E1;
                    background-color: #F8FAFC;
                }
            """)

    def _on_toggled(self, _checked: bool) -> None:
        self._update_style()


class SettingRowCard(QFrame):
    """Windows 11 Settings item row with Fluent vector icon, title, description, and action widget."""

    def __init__(
        self,
        icon_name: str,
        title: str,
        desc: str,
        action_widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SettingRowCard")
        self.setStyleSheet("""
            QFrame#SettingRowCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(create_fluent_pixmap(icon_name, color="#0078D4", size=22))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_lbl)

        txt_box = QVBoxLayout()
        txt_box.setSpacing(2)

        t_lbl = QLabel(title, self)
        font = t_lbl.font()
        font.setBold(True)
        font.setPointSize(13)
        t_lbl.setFont(font)
        t_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        txt_box.addWidget(t_lbl)

        d_lbl = QLabel(desc, self)
        d_lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 12px; border: none; background: transparent;")
        txt_box.addWidget(d_lbl)
        layout.addLayout(txt_box, 1)

        layout.addWidget(action_widget)


class SettingsPage(QWidget):
    """Application settings page with Windows 11 Fluent layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._load_values()

    def _init_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget(scroll)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title_lbl = QLabel("设置中心", container)
        font = title_lbl.font()
        font.setPointSize(16)
        font.setBold(True)
        title_lbl.setFont(font)
        title_lbl.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        title_box.addWidget(title_lbl)

        desc_lbl = QLabel("个性化配置壁纸呈现样式、文件保存位置、缓存清理与 Windows 系统深度集成", container)
        desc_lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 12px; border: none; background: transparent;")
        title_box.addWidget(desc_lbl)
        layout.addLayout(title_box)

        # 1. Wallpaper Style Placement Card
        style_card = QFrame(container)
        style_card.setObjectName("SettingsStyleCard")
        style_card.setStyleSheet("QFrame#SettingsStyleCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; }")
        sc_layout = QVBoxLayout(style_card)
        sc_layout.setContentsMargins(20, 16, 20, 16)
        sc_layout.setSpacing(12)

        sc_title = QLabel("Windows 桌面壁纸呈现样式", style_card)
        font = sc_title.font()
        font.setBold(True)
        font.setPointSize(13)
        sc_title.setFont(font)
        sc_title.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        sc_layout.addWidget(sc_title)

        self.style_group = QButtonGroup(self)
        self.style_group.setExclusive(True)
        style_grid = QGridLayout()
        style_grid.setSpacing(10)

        current_style = config.wallpaper_style
        for idx, (key, info) in enumerate(WALLPAPER_STYLES.items()):
            r = idx // 2
            c = idx % 2
            card_btn = StyleOptionCard(key, info["name"], info["desc"], style_card)
            if key == current_style:
                card_btn.setChecked(True)
            self.style_group.addButton(card_btn)
            k = key
            card_btn.toggled.connect(lambda chk, sk=k: self._on_style_selected(chk, sk))
            style_grid.addWidget(card_btn, r, c)

        sc_layout.addLayout(style_grid)
        layout.addWidget(style_card)

        # 2. Download Directory Card
        dl_card = QFrame(container)
        dl_card.setObjectName("SettingsDlCard")
        dl_card.setStyleSheet("QFrame#SettingsDlCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; }")
        dl_layout = QVBoxLayout(dl_card)
        dl_layout.setContentsMargins(20, 16, 20, 16)
        dl_layout.setSpacing(10)

        dl_title = QLabel("壁纸下载与保存目录", dl_card)
        font = dl_title.font()
        font.setBold(True)
        font.setPointSize(13)
        dl_title.setFont(font)
        dl_title.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        dl_layout.addWidget(dl_title)

        dl_row = QHBoxLayout()
        self.path_input = QLineEdit(config.download_dir, dl_card)
        self.path_input.setReadOnly(True)
        self.path_input.setFixedHeight(36)
        dl_row.addWidget(self.path_input, 1)

        self.browse_btn = QPushButton("更改目录...", dl_card)
        self.browse_btn.setIcon(create_icon("folder_open", color="#475569", size=14))
        self.browse_btn.setFixedHeight(36)
        self.browse_btn.clicked.connect(self._on_browse_dir)
        dl_row.addWidget(self.browse_btn)

        self.open_dir_btn = QPushButton("打开文件夹", dl_card)
        self.open_dir_btn.setIcon(create_icon("folder", color="#475569", size=14))
        self.open_dir_btn.setFixedHeight(36)
        self.open_dir_btn.clicked.connect(self._on_open_dir)
        dl_row.addWidget(self.open_dir_btn)

        dl_layout.addLayout(dl_row)
        layout.addWidget(dl_card)

        # 3. Cache Management Card
        cache_card = QFrame(container)
        cache_card.setObjectName("SettingsCacheCard")
        cache_card.setStyleSheet("QFrame#SettingsCacheCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; }")
        cc_layout = QVBoxLayout(cache_card)
        cc_layout.setContentsMargins(20, 16, 20, 16)
        cc_layout.setSpacing(10)

        cc_title = QLabel("本地图片缓存管理", cache_card)
        font = cc_title.font()
        font.setBold(True)
        font.setPointSize(13)
        cc_title.setFont(font)
        cc_title.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        cc_layout.addWidget(cc_title)

        cc_row = QHBoxLayout()
        self.cache_size_lbl = QLabel(f"已占用缓存: {cache_mgr.get_cache_size_mb_str()}", cache_card)
        self.cache_size_lbl.setStyleSheet("color: #475569; font-size: 13px; border: none; background: transparent;")
        cc_row.addWidget(self.cache_size_lbl)

        cc_row.addStretch()

        self.clear_cache_btn = QPushButton("清理全部缓存", cache_card)
        self.clear_cache_btn.setIcon(create_icon("trash", color="#475569", size=14))
        self.clear_cache_btn.setFixedHeight(36)
        self.clear_cache_btn.clicked.connect(self._on_clear_cache)
        cc_row.addWidget(self.clear_cache_btn)

        cc_layout.addLayout(cc_row)
        layout.addWidget(cache_card)

        # 4. Windows 11 Style System Switches
        sys_vbox = QVBoxLayout()
        sys_vbox.setSpacing(8)

        sys_hdr = QLabel("Windows 系统集成与选项", container)
        font = sys_hdr.font()
        font.setBold(True)
        font.setPointSize(13)
        sys_hdr.setFont(font)
        sys_hdr.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        sys_vbox.addWidget(sys_hdr)

        # Switch 1: Startup
        self.startup_switch = SwitchToggle(container)
        self.startup_switch.setChecked(wallpaper_setter.is_startup_enabled() or config.start_with_windows)
        self.startup_switch.toggled.connect(self._on_startup_toggled)
        row1 = SettingRowCard("power", "开机自动启动", "随 Windows 系统开机在后台静默启动运行", self.startup_switch, container)
        sys_vbox.addWidget(row1)

        # Switch 2: Close to Tray
        self.close_switch = SwitchToggle(container)
        self.close_switch.setChecked(config.close_to_tray)
        self.close_switch.toggled.connect(lambda chk: config.set("close_to_tray", chk))
        row2 = SettingRowCard("desktop", "关闭时最小化到托盘", "点击窗口右上角关闭按钮时，保持后台运行而不退出软件", self.close_switch, container)
        sys_vbox.addWidget(row2)

        # Switch 3: Tray Notification
        self.notify_switch = SwitchToggle(container)
        self.notify_switch.setChecked(config.tray_notifications)
        self.notify_switch.toggled.connect(lambda chk: config.set("tray_notifications", chk))
        row3 = SettingRowCard("bell", "桌面悬浮通知消息", "更换壁纸时在屏幕右下角弹出精美的实时进度与完成气泡", self.notify_switch, container)
        sys_vbox.addWidget(row3)

        layout.addLayout(sys_vbox)

        # 5. About Card
        about_card = QFrame(container)
        about_card.setObjectName("SettingsAboutCard")
        about_card.setStyleSheet("QFrame#SettingsAboutCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; }")
        ab_layout = QVBoxLayout(about_card)
        ab_layout.setContentsMargins(20, 16, 20, 16)
        ab_layout.setSpacing(8)

        ab_title = QLabel(f"关于 {APP_NAME} v{APP_VERSION}", about_card)
        font = ab_title.font()
        font.setBold(True)
        font.setPointSize(13)
        ab_title.setFont(font)
        ab_title.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        ab_layout.addWidget(ab_title)

        info_text = (
            f"• 软件名称: 星澜壁纸 (Stellar Wallpaper) v{APP_VERSION}<br>"
            "• 开源主页: <a href=\"https://github.com/zero-ljz/stellar-wallpaper\" style=\"color: #0078D4; text-decoration: none; font-weight: 600;\">https://github.com/zero-ljz/stellar-wallpaper</a><br>"
            "• 操作系统: 兼容 Windows 10 & 11 (64-bit)<br>"
            "• 渲染引擎: 现代轻量化 Fluent 2 Light Engine<br>"
            "• 专属字体: MiSans (小米高品质清晰字库)<br>"
            "• 壁纸画廊: 18 大精选主题与图源 (含 4K 专区、必应历史大图库、Picsum 摄影图库)"
        )
        ab_desc = QLabel(info_text, about_card)
        ab_desc.setTextFormat(Qt.TextFormat.RichText)
        ab_desc.setOpenExternalLinks(True)
        ab_desc.setStyleSheet("color: #475569; font-weight: 500; font-size: 12px; line-height: 1.8; border: none; background: transparent;")
        ab_layout.addWidget(ab_desc)

        github_btn = QPushButton("访问 GitHub 开源仓库", about_card)
        github_btn.setIcon(create_icon("link", color="#0078D4", size=14))
        github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        github_btn.setFixedHeight(30)
        github_btn.setFixedWidth(160)
        github_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #0078D4;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #DBEAFE;
                border-color: #93C5FD;
                color: #005A9E;
            }
        """)
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/zero-ljz/stellar-wallpaper")))
        ab_layout.addWidget(github_btn)

        layout.addWidget(about_card)
        layout.addStretch()

        scroll.setWidget(container)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _load_values(self) -> None:
        self.path_input.setText(config.download_dir)
        self.cache_size_lbl.setText(f"已占用缓存: {cache_mgr.get_cache_size_mb_str()}")

    def _on_style_selected(self, checked: bool, style_key: str) -> None:
        if checked:
            config.wallpaper_style = style_key
            wallpaper_setter.set_wallpaper_style(style_key)

    def _on_browse_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "选择壁纸保存目录", config.download_dir)
        if dir_path:
            config.download_dir = dir_path
            self.path_input.setText(dir_path)

    def _on_open_dir(self) -> None:
        path = Path(config.download_dir)
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))

    def _on_clear_cache(self) -> None:
        if show_question(
            self,
            "确认清理",
            "确定要清理所有本地缓存图片吗？已保存到下载目录的壁纸不受影响。",
        ):
            count, freed = cache_mgr.clear_cache()
            mb = freed / (1024 * 1024)
            self.cache_size_lbl.setText(f"已占用缓存: {cache_mgr.get_cache_size_mb_str()}")
            show_success(self, "清理完成", f"已成功清理 {count} 个缓存文件，释放 {mb:.2f} MB 空间。")

    def _on_startup_toggled(self, enabled: bool) -> None:
        config.start_with_windows = enabled
        wallpaper_setter.set_startup_with_windows(enabled)
