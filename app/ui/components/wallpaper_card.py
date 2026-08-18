"""Polished modern wallpaper card component."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...config import config
from ...core.api_client import api_client
from ...core.database import db
from ...core.image_loader import image_loader


class WallpaperCard(QFrame):
    """Card widget representing a single wallpaper with async thumbnail and hover actions."""

    apply_requested = Signal(dict)
    preview_requested = Signal(dict)
    favorite_toggled = Signal(dict, bool)

    def __init__(self, item_data: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item_data = dict(item_data)
        self.setFixedSize(264, 196)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("WallpaperCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._pixmap: QPixmap | None = None
        self._is_hovered = False
        self._is_favorited = db.is_favorite(
            str(self.item_data.get("id") or self.item_data.get("wallpaper_id") or self.item_data.get("url") or "")
        )

        self._init_ui()
        self._load_thumbnail()

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            QFrame#WallpaperCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#WallpaperCard:hover {
                border-color: #0078D4;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Image Container (16:9 ratio approx 264 x 146)
        self.img_container = QWidget(self)
        self.img_container.setFixedHeight(146)
        img_layout = QVBoxLayout(self.img_container)
        img_layout.setContentsMargins(8, 8, 8, 8)
        img_layout.setSpacing(0)

        # Top tag row inside image
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        cat_name = self.item_data.get("category_name") or "壁纸"
        self.cat_badge = QLabel(cat_name, self.img_container)
        self.cat_badge.setStyleSheet("""
            background-color: rgba(15, 23, 42, 0.7);
            color: #FFFFFF;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 10px;
            border: none;
        """)
        top_row.addWidget(self.cat_badge)

        resolution = self.item_data.get("resolution", "")
        if resolution:
            self.res_badge = QLabel(resolution, self.img_container)
            self.res_badge.setStyleSheet("""
                background-color: rgba(0, 120, 212, 0.85);
                color: #FFFFFF;
                font-size: 10px;
                font-weight: 500;
                padding: 2px 8px;
                border-radius: 10px;
                border: none;
            """)
            top_row.addWidget(self.res_badge)


        top_row.addStretch()

        # Favorite star button on top-right
        self.fav_btn = QPushButton("★" if self._is_favorited else "☆", self.img_container)
        self.fav_btn.setFixedSize(26, 26)
        self._update_fav_style()
        self.fav_btn.clicked.connect(self._toggle_favorite)
        top_row.addWidget(self.fav_btn)

        img_layout.addLayout(top_row)
        img_layout.addStretch()

        # Bottom action overlay row (appears on hover)
        self.action_row_widget = QWidget(self.img_container)
        action_layout = QHBoxLayout(self.action_row_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)

        self.apply_btn = QPushButton("设为壁纸", self.action_row_widget)
        self.apply_btn.setFixedHeight(28)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #1084D9; }
            QPushButton:pressed { background-color: #006CBE; }
        """)
        self.apply_btn.clicked.connect(lambda: self.apply_requested.emit(self.item_data))
        action_layout.addWidget(self.apply_btn, 1)

        self.preview_btn = QPushButton("🔍", self.action_row_widget)
        self.preview_btn.setToolTip("查看大图")
        self.preview_btn.setFixedSize(28, 28)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(17, 24, 39, 0.8);
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(17, 24, 39, 0.95); }
        """)
        self.preview_btn.clicked.connect(lambda: self.preview_requested.emit(self.item_data))
        action_layout.addWidget(self.preview_btn)

        self.download_btn = QPushButton("💾", self.action_row_widget)
        self.download_btn.setToolTip("保存原图")
        self.download_btn.setFixedSize(28, 28)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(17, 24, 39, 0.8);
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(17, 24, 39, 0.95); }
        """)
        self.download_btn.clicked.connect(self._on_download_clicked)
        action_layout.addWidget(self.download_btn)

        self.action_row_widget.hide()
        img_layout.addWidget(self.action_row_widget)
        layout.addWidget(self.img_container)

        # Footer info area
        footer = QWidget(self)
        footer.setFixedHeight(48)
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(10, 6, 10, 6)
        footer_layout.setSpacing(2)

        raw_title = self.item_data.get("title") or self.item_data.get("tag") or "高清壁纸"
        clean_title = raw_title.replace("_360Wallpaper_", "").replace("_category_", "").replace("_", " ").strip()
        self.title_label = QLabel(clean_title or "高清壁纸", footer)
        self.title_label.setStyleSheet("color: #0B0F19; font-weight: 700; font-size: 12px; border: none; background: transparent;")
        footer_layout.addWidget(self.title_label)

        raw_sub = self.item_data.get("applied_at") or self.item_data.get("resolution") or ""
        self.sub_label = QLabel(raw_sub, footer)
        self.sub_label.setStyleSheet("color: #334155; font-weight: 600; font-size: 11px; border: none; background: transparent;")
        footer_layout.addWidget(self.sub_label)

        layout.addWidget(footer)

    def _update_fav_style(self) -> None:
        if self._is_favorited:
            self.fav_btn.setText("★")
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEF3C7;
                    color: #D97706;
                    border: none;
                    border-radius: 13px;
                    font-size: 14px;
                }
            """)
        else:
            self.fav_btn.setText("☆")
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 0, 0, 0.45);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 13px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.75);
                }
            """)


    def _toggle_favorite(self) -> None:
        self._is_favorited = not self._is_favorited
        wid = str(self.item_data.get("id") or self.item_data.get("wallpaper_id") or self.item_data.get("url") or "")
        if self._is_favorited:
            db.add_favorite(self.item_data)
        else:
            db.remove_favorite(wid)
        self._update_fav_style()
        self.favorite_toggled.emit(self.item_data, self._is_favorited)

    def _on_download_clicked(self) -> None:
        url = self.item_data.get("url") or self.item_data.get("url_mid") or ""
        if not url:
            return

        save_dir = Path(config.download_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = f"Wallpaper_{self.item_data.get('id', 'pic')}_{int(hash(url)) & 0xFFFFFF}.jpg"
        target = save_dir / filename

        ok = api_client.download_image(url, target)
        if ok:
            QMessageBox.information(self, "保存成功", f"壁纸已成功保存至:\n{target}")
        else:
            QMessageBox.warning(self, "保存失败", "下载壁纸失败，请检查网络连接")

    def _load_thumbnail(self) -> None:
        url = (
            self.item_data.get("thumb_url")
            or self.item_data.get("url_thumb")
            or self.item_data.get("url_mid")
            or self.item_data.get("url")
            or ""
        )
        local_path = self.item_data.get("local_path", "")
        image_loader.load_thumbnail(url, local_path, self._on_thumbnail_loaded)

    def _on_thumbnail_loaded(self, pix: QPixmap) -> None:
        if not pix.isNull():
            self._pixmap = pix
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        img_rect = QRect(0, 0, self.width(), 146)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        painter.setClipPath(path)

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                img_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - img_rect.width()) // 2
            y = (scaled.height() - img_rect.height()) // 2
            painter.drawPixmap(img_rect, scaled, QRect(x, y, img_rect.width(), img_rect.height()))
        else:
            painter.fillRect(img_rect, QColor("#F1F5F9"))
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(img_rect, Qt.AlignmentFlag.AlignCenter, "加载中...")

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self._is_hovered = True
        self.action_row_widget.show()

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self._is_hovered = False
        self.action_row_widget.hide()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.preview_requested.emit(self.item_data)
        super().mousePressEvent(event)
