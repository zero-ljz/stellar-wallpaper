"""Unit tests for constants and configuration management."""

import tempfile
from pathlib import Path
from app.constants import CATEGORIES, CATEGORY_MAP, WALLPAPER_STYLES
from app.config import ConfigManager


def test_categories_count():
    assert len(CATEGORIES) == 15
    assert "36" in CATEGORY_MAP
    assert CATEGORY_MAP["36"] == "4K专区"
    assert CATEGORY_MAP["9"] == "风景大片"
    assert CATEGORY_MAP["26"] == "动漫卡通"
    assert CATEGORY_MAP["35"] == "文字控"


def test_wallpaper_styles():
    assert "fill" in WALLPAPER_STYLES
    assert "fit" in WALLPAPER_STYLES
    assert "stretch" in WALLPAPER_STYLES
    assert "tile" in WALLPAPER_STYLES
    assert "center" in WALLPAPER_STYLES
    assert "span" in WALLPAPER_STYLES


def test_config_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = ConfigManager(Path(tmpdir))
        assert cfg.auto_switch_enabled is False
        assert cfg.wallpaper_style == "fill"

        cfg.auto_switch_enabled = True
        cfg.wallpaper_style = "fit"
        cfg.selected_categories = ["36", "9"]

        # Reload from disk
        cfg2 = ConfigManager(Path(tmpdir))
        assert cfg2.auto_switch_enabled is True
        assert cfg2.wallpaper_style == "fit"
        assert cfg2.selected_categories == ["36", "9"]
