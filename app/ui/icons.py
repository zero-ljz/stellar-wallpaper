"""High-DPI Microsoft Fluent System Icons provider for Windows 11 / Fusion Light theme.

Renders official offline Fluent vector SVGs at any DPI with dynamic color tinting.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

FLUENT_ICONS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "resources" / "icons" / "fluent"

# Name aliases to exact Fluent SVG file base names
ICON_NAME_MAP: Final[dict[str, str]] = {
    # Navigation & Core
    "gallery": "image_multiple_24_regular",
    "image": "image_24_regular",
    "images": "image_multiple_24_regular",
    "shuffle": "arrow_shuffle_24_regular",
    "switch": "arrow_shuffle_24_regular",
    "random": "arrow_shuffle_24_regular",
    "timer": "timer_24_regular",
    "clock": "clock_24_regular",
    "heart": "heart_24_regular",
    "heart_filled": "heart_24_filled",
    "history": "history_24_regular",
    "settings": "settings_24_regular",
    # Actions & States
    "star": "star_24_regular",
    "star_outline": "star_24_regular",
    "star_filled": "star_24_filled",
    "search": "search_24_regular",
    "preview": "zoom_in_24_regular",
    "zoom_in": "zoom_in_24_regular",
    "maximize": "full_screen_maximize_24_regular",
    "eye": "eye_24_regular",
    "download": "arrow_download_24_regular",
    "save": "save_24_regular",
    "refresh": "arrow_clockwise_24_regular",
    "sync": "arrow_sync_24_regular",
    "reset": "arrow_counterclockwise_24_regular",
    "folder": "folder_24_regular",
    "folder_open": "folder_open_24_regular",
    "trash": "delete_24_regular",
    "delete": "delete_24_regular",
    "close": "dismiss_24_regular",
    "dismiss": "dismiss_24_regular",
    "dismiss_circle": "dismiss_circle_24_regular",
    "check": "checkmark_24_regular",
    "check_circle": "checkmark_circle_24_regular",
    "check_circle_filled": "checkmark_circle_24_filled",
    "warning": "warning_24_regular",
    "warning_filled": "warning_24_filled",
    "info": "info_24_regular",
    "info_filled": "info_24_filled",
    "question": "question_circle_24_regular",
    "play": "play_24_regular",
    "play_filled": "play_24_filled",
    "pause": "pause_24_regular",
    "pause_filled": "pause_24_filled",
    "skip_forward": "next_24_regular",
    "power": "power_24_regular",
    "bell": "alert_24_regular",
    "desktop": "desktop_24_regular",
    "sparkle": "sparkle_24_regular",
    "sparkle_filled": "sparkle_24_filled",
    "flash": "flash_24_regular",
    "flash_filled": "flash_24_filled",
    "chevron_left": "chevron_left_24_regular",
    "chevron_right": "chevron_right_24_regular",
    "chevron_up": "chevron_up_24_regular",
    "chevron_down": "chevron_down_24_regular",
    "arrow_left": "arrow_left_24_regular",
    "arrow_jump": "arrow_enter_left_24_regular",
    # Categories & Sources (360 Wallpaper, Bing, Lorem Picsum)
    "cat_latest": "flash_24_filled",
    "cat_bing": "weather_sunny_24_regular",
    "cat_picsum": "camera_24_regular",
    "cat_4k": "sparkle_24_filled",
    "cat_landscape": "weather_sunny_24_regular",
    "cat_anime": "paint_brush_24_regular",
    "cat_game": "games_24_regular",
    "cat_car": "vehicle_car_24_regular",
    "cat_pet": "animal_cat_24_regular",
    "cat_beauty": "person_24_regular",
    "cat_fashion": "glasses_24_regular",
    "cat_fresh": "leaf_two_24_regular",
    "cat_movie": "movies_and_tv_24_regular",
    "cat_love": "heart_24_regular",
    "cat_star": "star_24_regular",
    "cat_military": "shield_24_regular",
    "cat_sports": "trophy_24_regular",
    "cat_text": "text_description_24_regular",
    "cat_camera": "camera_24_regular",
}

# In-memory raw SVG string cache
_RAW_SVG_CACHE: dict[str, str] = {}


def _get_raw_svg(icon_key: str) -> str | None:
    file_base = ICON_NAME_MAP.get(icon_key, icon_key)
    if file_base in _RAW_SVG_CACHE:
        return _RAW_SVG_CACHE[file_base]

    svg_file = FLUENT_ICONS_DIR / f"{file_base}.svg"
    if not svg_file.exists():
        # Try finding partial match in folder
        candidates = list(FLUENT_ICONS_DIR.glob(f"{file_base}*.svg"))
        if candidates:
            svg_file = candidates[0]
        else:
            return None

    try:
        content = svg_file.read_text(encoding="utf-8")
        _RAW_SVG_CACHE[file_base] = content
        return content
    except Exception:
        return None


def get_tinted_svg_data(name: str, color: str = "#475569") -> QByteArray | None:
    """Load and tint a Fluent SVG with a specific color."""
    raw = _get_raw_svg(name)
    if not raw:
        return None

    # Replace currentColor, #212121, or add fill attribute
    hex_color = color.strip()
    colored = re.sub(r'fill="[^"]+"', f'fill="{hex_color}"', raw)
    colored = colored.replace("currentColor", hex_color)
    if 'fill="' not in colored:
        colored = colored.replace("<path ", f'<path fill="{hex_color}" ')
        colored = colored.replace("<svg ", f'<svg fill="{hex_color}" ')

    return QByteArray(colored.encode("utf-8"))


def create_fluent_pixmap(
    name: str,
    color: str = "#475569",
    size: int = 24,
    dpr: float = 1.0,
) -> QPixmap:
    """Renders a pixel-perfect, high-DPI aware QPixmap from Fluent SVG."""
    svg_bytes = get_tinted_svg_data(name, color)
    if not svg_bytes:
        # Fallback empty transparent pixmap
        pix = QPixmap(int(size * dpr), int(size * dpr))
        pix.fill(Qt.GlobalColor.transparent)
        pix.setDevicePixelRatio(dpr)
        return pix

    renderer = QSvgRenderer(svg_bytes)
    pixel_size = max(1, int(round(size * dpr)))
    pixmap = QPixmap(pixel_size, pixel_size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, pixel_size, pixel_size))
    painter.end()

    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def create_fluent_icon(name: str, color: str = "#475569", size: int = 24) -> QIcon:
    """Creates a multi-resolution High-DPI QIcon from Fluent SVG (crisp on 100% ~ 250% scaling)."""
    icon = QIcon()
    for scale in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5):
        pix = create_fluent_pixmap(name, color, size=size, dpr=scale)
        icon.addPixmap(pix)
    return icon


def create_icon(name: str, color: str = "#475569", size: int = 24) -> QIcon:
    """Primary icon factory for navigation, cards, and buttons."""
    return create_fluent_icon(name, color, size)
