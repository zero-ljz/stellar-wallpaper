"""Windows wallpaper setting and registry style configuration for Windows 10/11."""

from __future__ import annotations

import ctypes
import os
import sys
import winreg
from pathlib import Path
from typing import Any

from ..constants import APP_NAME, WALLPAPER_STYLES

SPI_SETDESKWALLPAPER = 20
SPI_GETDESKWALLPAPER = 115
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


class WallpaperSetter:
    """Handles setting Windows desktop wallpaper and styling."""

    @staticmethod
    def set_wallpaper_style(style_key: str = "fill") -> bool:
        """Configures the wallpaper positioning style in Windows Registry."""
        if sys.platform != "win32":
            return False

        style_info = WALLPAPER_STYLES.get(style_key, WALLPAPER_STYLES["fill"])
        style_val = style_info["style"]
        tile_val = style_info["tile"]

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Control Panel\Desktop",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, style_val)
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, tile_val)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Failed to set wallpaper style registry: {e}")
            return False

    @classmethod
    def apply_wallpaper(cls, image_path: str | Path, style_key: str = "fill") -> bool:
        """Sets the specified image file as Windows desktop wallpaper."""
        if sys.platform != "win32":
            print(f"[Mock] Set wallpaper: {image_path} with style {style_key}")
            return True

        path_obj = Path(image_path).resolve()
        if not path_obj.exists():
            print(f"Wallpaper file does not exist: {path_obj}")
            return False

        abs_path = str(path_obj)

        # Set style in registry first
        cls.set_wallpaper_style(style_key)

        # Call SystemParametersInfoW to apply and broadcast
        try:
            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                abs_path,
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
            )
            return bool(result)
        except Exception as e:
            print(f"SystemParametersInfoW error: {e}")
            return False

    @staticmethod
    def get_current_wallpaper_path() -> str:
        """Gets current Windows wallpaper path."""
        if sys.platform != "win32":
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_GETDESKWALLPAPER,
                len(buffer),
                buffer,
                0,
            )
            return buffer.value
        except Exception:
            return ""

    @staticmethod
    def set_startup_with_windows(enable: bool) -> bool:
        """Sets application startup on Windows boot via Registry Run key."""
        if sys.platform != "win32":
            return False
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
            )
            if enable:
                # Get current executable command line
                if getattr(sys, "frozen", False):
                    exe_path = f'"{sys.executable}"'
                else:
                    exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Failed to configure startup registry: {e}")
            return False

    @staticmethod
    def is_startup_enabled() -> bool:
        """Checks if startup is enabled in registry."""
        if sys.platform != "win32":
            return False
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_QUERY_VALUE,
            )
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return bool(val)
        except Exception:
            return False


# Global singleton instance
wallpaper_setter = WallpaperSetter()
