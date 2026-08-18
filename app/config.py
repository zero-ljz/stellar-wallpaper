"""Configuration management with JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import (
    CATEGORIES,
    DEFAULT_APP_DATA_DIR,
    DEFAULT_DOWNLOAD_DIR,
)


class ConfigManager:
    """Manages application settings persistently with auto-save."""

    DEFAULT_CONFIG: dict[str, Any] = {
        "selected_categories": [c["id"] for c in CATEGORIES],  # default all selected
        "auto_switch_enabled": False,
        "auto_switch_interval": 1800,  # 30 minutes in seconds
        "auto_switch_source": "categories",  # "categories" or "favorites"
        "auto_switch_on_startup": False,
        "wallpaper_style": "fill",  # fill, fit, stretch, tile, center, span
        "download_dir": str(DEFAULT_DOWNLOAD_DIR),
        "minimize_to_tray": True,
        "close_to_tray": True,
        "tray_notifications": True,
        "start_with_windows": False,
        "max_cache_mb": 500,
        "last_wallpaper": None,  # dict of metadata
    }

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or DEFAULT_APP_DATA_DIR
        self.config_file = self.config_dir / "config.json"
        self._config: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from disk or create default."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._config = {**self.DEFAULT_CONFIG, **loaded}
                    return
            except Exception:
                pass
        self._config = dict(self.DEFAULT_CONFIG)
        self.save()

    def save(self) -> None:
        """Save current configuration to disk."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, self.DEFAULT_CONFIG.get(key, default))

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        self._config[key] = value
        if auto_save:
            self.save()

    # Convenience properties
    @property
    def selected_categories(self) -> list[str]:
        return self.get("selected_categories", [c["id"] for c in CATEGORIES])

    @selected_categories.setter
    def selected_categories(self, value: list[str]) -> None:
        self.set("selected_categories", value)

    @property
    def auto_switch_enabled(self) -> bool:
        return bool(self.get("auto_switch_enabled", False))

    @auto_switch_enabled.setter
    def auto_switch_enabled(self, value: bool) -> None:
        self.set("auto_switch_enabled", value)

    @property
    def auto_switch_interval(self) -> int:
        return int(self.get("auto_switch_interval", 1800))

    @auto_switch_interval.setter
    def auto_switch_interval(self, value: int) -> None:
        self.set("auto_switch_interval", value)

    @property
    def auto_switch_source(self) -> str:
        return str(self.get("auto_switch_source", "categories"))

    @auto_switch_source.setter
    def auto_switch_source(self, value: str) -> None:
        self.set("auto_switch_source", value)

    @property
    def wallpaper_style(self) -> str:
        return str(self.get("wallpaper_style", "fill"))

    @wallpaper_style.setter
    def wallpaper_style(self, value: str) -> None:
        self.set("wallpaper_style", value)

    @property
    def download_dir(self) -> str:
        return str(self.get("download_dir", str(DEFAULT_DOWNLOAD_DIR)))

    @download_dir.setter
    def download_dir(self, value: str) -> None:
        self.set("download_dir", value)

    @property
    def minimize_to_tray(self) -> bool:
        return bool(self.get("minimize_to_tray", True))

    @minimize_to_tray.setter
    def minimize_to_tray(self, value: bool) -> None:
        self.set("minimize_to_tray", value)

    @property
    def close_to_tray(self) -> bool:
        return bool(self.get("close_to_tray", True))

    @close_to_tray.setter
    def close_to_tray(self, value: bool) -> None:
        self.set("close_to_tray", value)

    @property
    def tray_notifications(self) -> bool:
        return bool(self.get("tray_notifications", True))

    @tray_notifications.setter
    def tray_notifications(self, value: bool) -> None:
        self.set("tray_notifications", value)

    @property
    def start_with_windows(self) -> bool:
        return bool(self.get("start_with_windows", False))

    @start_with_windows.setter
    def start_with_windows(self, value: bool) -> None:
        self.set("start_with_windows", value)

    @property
    def last_wallpaper(self) -> dict[str, Any] | None:
        return self.get("last_wallpaper", None)

    @last_wallpaper.setter
    def last_wallpaper(self, value: dict[str, Any] | None) -> None:
        self.set("last_wallpaper", value)


# Global singleton instance
config = ConfigManager()
