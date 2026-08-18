"""Polished auto-rotation scheduler page with digital countdown and modern controls."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...config import config
from ...constants import INTERVAL_OPTIONS
from ...core.scheduler import scheduler
from ..components.switch_toggle import SwitchToggle


class IntervalChipButton(QPushButton):
    """Modern interactive segmented chip button for interval selection."""

    def __init__(self, label: str, seconds: int, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.seconds = seconds
        self.setProperty("class", "IntervalChip")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)


class SchedulerPage(QWidget):
    """Configuration page for automatic wallpaper rotation with digital countdown."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._interval_chips: list[IntervalChipButton] = []
        self._init_ui()
        self._load_config()

        # Connect scheduler signals
        scheduler.countdown_tick.connect(self._on_countdown_tick)
        scheduler.status_changed.connect(self._on_status_changed)

    def _init_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget(scroll)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        # 1. Main Status & Countdown Card
        status_card = QFrame(container)
        status_card.setObjectName("SchedulerStatusCard")
        status_card.setStyleSheet("""
            QFrame#SchedulerStatusCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(20, 16, 20, 16)
        sc_layout.setSpacing(14)

        # Toggle status row
        toggle_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.status_title = QLabel("自动轮播状态: 未开启", status_card)
        font = self.status_title.font()
        font.setPointSize(15)
        font.setBold(True)
        self.status_title.setFont(font)
        self.status_title.setStyleSheet("border: none; background: transparent;")
        title_box.addWidget(self.status_title)

        desc_lbl = QLabel("开启后，软件将在后台按照设定的时间间隔自动更换桌面壁纸", status_card)
        desc_lbl.setStyleSheet("color: #475569; font-weight: 500; font-size: 12px; border: none; background: transparent;")
        title_box.addWidget(desc_lbl)
        toggle_row.addLayout(title_box)

        toggle_row.addStretch()

        self.toggle_btn = QPushButton("▶ 开启自动换壁纸", status_card)
        self.toggle_btn.setProperty("class", "PrimaryButton")
        self.toggle_btn.setFixedSize(160, 38)
        font = self.toggle_btn.font()
        font.setBold(True)
        self.toggle_btn.setFont(font)
        self.toggle_btn.clicked.connect(self._toggle_scheduler)
        toggle_row.addWidget(self.toggle_btn)
        sc_layout.addLayout(toggle_row)

        # Divider
        div = QFrame(status_card)
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #E2E8F0; border: none; background: #E2E8F0; max-height: 1px;")
        sc_layout.addWidget(div)

        # Live Digital Countdown Clock Display
        cd_row = QHBoxLayout()
        cd_lbl = QLabel("⏱️ 距离下次壁纸切换剩余时间:", status_card)
        cd_lbl.setStyleSheet("color: #475569; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        cd_row.addWidget(cd_lbl)

        cd_row.addStretch()

        self.countdown_display = QLabel("-- : -- : --", status_card)
        font = self.countdown_display.font()
        font.setFamily("Consolas, Courier New, Segoe UI")
        font.setPointSize(22)
        font.setBold(True)
        self.countdown_display.setFont(font)
        self.countdown_display.setStyleSheet("color: #0078D4; letter-spacing: 2px; border: none; background: transparent;")
        cd_row.addWidget(self.countdown_display)

        cd_row.addSpacing(16)

        self.next_now_btn = QPushButton("⚡ 立即换下一张", status_card)
        self.next_now_btn.clicked.connect(lambda: scheduler.trigger_switch(source=config.auto_switch_source))
        cd_row.addWidget(self.next_now_btn)

        self.reset_cd_btn = QPushButton("🔄 重置计时", status_card)
        self.reset_cd_btn.clicked.connect(scheduler.reset_timer)
        cd_row.addWidget(self.reset_cd_btn)

        sc_layout.addLayout(cd_row)

        # Countdown Progress Bar
        self.countdown_bar = QProgressBar(status_card)
        self.countdown_bar.setFixedHeight(5)
        self.countdown_bar.setTextVisible(False)
        self.countdown_bar.setValue(100)
        sc_layout.addWidget(self.countdown_bar)

        layout.addWidget(status_card)

        # 2. Interval Selection Card
        interval_card = QFrame(container)
        interval_card.setObjectName("SchedulerIntervalCard")
        interval_card.setStyleSheet("""
            QFrame#SchedulerIntervalCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)
        ic_layout = QVBoxLayout(interval_card)
        ic_layout.setContentsMargins(20, 16, 20, 16)
        ic_layout.setSpacing(12)

        ic_title = QLabel("⏱️ 轮播时间间隔设置", interval_card)
        font = ic_title.font()
        font.setBold(True)
        font.setPointSize(13)
        ic_title.setFont(font)
        ic_title.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        ic_layout.addWidget(ic_title)

        self.interval_group = QButtonGroup(self)
        grid = QGridLayout()
        grid.setSpacing(10)

        current_interval = config.auto_switch_interval
        cols = 3
        for idx, opt in enumerate(INTERVAL_OPTIONS):
            r = idx // cols
            c = idx % cols
            chip = IntervalChipButton(opt["label"], opt["seconds"], interval_card)
            if current_interval == opt["seconds"]:
                chip.setChecked(True)
            self.interval_group.addButton(chip)
            self._interval_chips.append(chip)
            sec = opt["seconds"]
            chip.toggled.connect(lambda chk, s=sec: self._on_interval_selected(chk, s))
            grid.addWidget(chip, r, c)

        # Custom minutes chip row
        custom_row = QHBoxLayout()
        self.custom_chip = IntervalChipButton("⏱️ 自定义时长", -1, interval_card)
        self.interval_group.addButton(self.custom_chip)
        custom_row.addWidget(self.custom_chip)

        self.custom_spinbox = QSpinBox(interval_card)
        self.custom_spinbox.setRange(1, 1440)
        self.custom_spinbox.setValue(max(1, current_interval // 60))
        self.custom_spinbox.setSuffix(" 分钟")
        self.custom_spinbox.setFixedWidth(130)
        self.custom_spinbox.setFixedHeight(38)
        self.custom_spinbox.valueChanged.connect(self._on_custom_minutes_changed)
        custom_row.addWidget(self.custom_spinbox)
        custom_row.addStretch()

        grid.addLayout(custom_row, len(INTERVAL_OPTIONS) // cols + 1, 0, 1, cols)
        ic_layout.addLayout(grid)
        layout.addWidget(interval_card)

        # 3. Source Selection Card
        opt_card = QFrame(container)
        opt_card.setObjectName("SchedulerOptCard")
        opt_card.setStyleSheet("""
            QFrame#SchedulerOptCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)
        oc_layout = QVBoxLayout(opt_card)
        oc_layout.setContentsMargins(20, 16, 20, 16)
        oc_layout.setSpacing(12)

        oc_title = QLabel("🎨 轮播壁纸来源", opt_card)
        font = oc_title.font()
        font.setBold(True)
        font.setPointSize(13)
        oc_title.setFont(font)
        oc_title.setStyleSheet("border: none; background: transparent; color: #0F172A;")
        oc_layout.addWidget(oc_title)

        source_row = QHBoxLayout()
        source_row.setSpacing(20)

        self.source_cat_rb = QRadioButton("从【随机分类池】中自动抽选", opt_card)
        self.source_fav_rb = QRadioButton("仅从【我的收藏】中循环轮播", opt_card)
        self.source_group = QButtonGroup(self)
        self.source_group.addButton(self.source_cat_rb)
        self.source_group.addButton(self.source_fav_rb)

        if config.auto_switch_source == "favorites":
            self.source_fav_rb.setChecked(True)
        else:
            self.source_cat_rb.setChecked(True)

        self.source_cat_rb.toggled.connect(self._on_source_changed)
        self.source_fav_rb.toggled.connect(self._on_source_changed)

        source_row.addWidget(self.source_cat_rb)
        source_row.addWidget(self.source_fav_rb)
        source_row.addStretch()
        oc_layout.addLayout(source_row)

        layout.addWidget(opt_card)
        layout.addStretch()

        scroll.setWidget(container)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _load_config(self) -> None:
        self._update_status_ui(scheduler.is_running)

    def _toggle_scheduler(self) -> None:
        if scheduler.is_running:
            scheduler.stop()
        else:
            scheduler.start()

    def _on_status_changed(self, is_running: bool) -> None:
        self._update_status_ui(is_running)

    def _update_status_ui(self, is_running: bool) -> None:
        if is_running:
            self.status_title.setText("自动轮播状态: 🟢 运行中")
            self.status_title.setStyleSheet("color: #10B981; font-weight: bold;")
            self.toggle_btn.setText("⏸ 暂停自动换壁纸")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #EF4444;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #DC2626; }
            """)
        else:
            self.status_title.setText("自动轮播状态: ⏸️ 已暂停")
            self.status_title.setStyleSheet("color: #64748B; font-weight: bold;")
            self.toggle_btn.setText("▶ 开启自动换壁纸")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078D4;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #1084D9; }
            """)

    def _on_countdown_tick(self, remaining: int, total: int) -> None:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        self.countdown_display.setText(f"{hours:02d} : {minutes:02d} : {seconds:02d}")

        if total > 0:
            pct = int((total - remaining) * 100 / total)
            self.countdown_bar.setValue(min(100, max(0, pct)))

    def _on_interval_selected(self, checked: bool, seconds: int) -> None:
        if checked:
            if seconds > 0:
                scheduler.set_interval(seconds)
            else:
                scheduler.set_interval(self.custom_spinbox.value() * 60)

    def _on_custom_minutes_changed(self, minutes: int) -> None:
        if self.custom_chip.isChecked():
            scheduler.set_interval(minutes * 60)

    def _on_source_changed(self) -> None:
        if self.source_fav_rb.isChecked():
            config.auto_switch_source = "favorites"
        else:
            config.auto_switch_source = "categories"
