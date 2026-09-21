"""Wallpaper setting and system integration for Windows and macOS."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    import winreg
else:
    winreg = None  # type: ignore

from ..constants import APP_ID, APP_NAME, WALLPAPER_STYLES

SPI_SETDESKWALLPAPER = 20
SPI_GETDESKWALLPAPER = 115
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


class WallpaperSetter:
    """Handles setting desktop wallpaper and styling on Windows and macOS."""

    @staticmethod
    def _get_macos_launch_agent_path() -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{APP_ID}.plist"

    @staticmethod
    def set_wallpaper_style(style_key: str = "fill") -> bool:
        """Configures the wallpaper positioning style in Windows Registry."""
        if sys.platform != "win32" or winreg is None:
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

    @staticmethod
    def _set_macos_wallpaper(abs_path: str) -> bool:
        """Sets macOS desktop wallpaper using AppleScript via osascript."""
        safe_path = abs_path.replace('"', '\\"')
        script = f'''
        tell application "System Events"
            tell every desktop
                set picture to "{safe_path}" as POSIX file
            end tell
        end tell
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return True

            fallback_script = f'''
            tell application "System Events"
                set picture of current desktop to "{safe_path}" as POSIX file
            end tell
            '''
            result2 = subprocess.run(
                ["osascript", "-e", fallback_script],
                capture_output=True,
                text=True,
                check=False,
            )
            if result2.returncode == 0:
                return True
            print(f"osascript failed: {result.stderr or result2.stderr}")
            return False
        except Exception as e:
            print(f"Failed to set macOS wallpaper: {e}")
            return False

    @classmethod
    def apply_wallpaper(cls, image_path: str | Path, style_key: str = "fill") -> bool:
        """Sets the specified image file as desktop wallpaper."""
        path_obj = Path(image_path).resolve()
        if not path_obj.exists():
            print(f"Wallpaper file does not exist: {path_obj}")
            return False

        abs_path = str(path_obj)

        if sys.platform == "darwin":
            return cls._set_macos_wallpaper(abs_path)

        if sys.platform != "win32":
            print(f"[Mock] Set wallpaper: {abs_path} with style {style_key}")
            return True

        # Set style in registry first on Windows
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

    @classmethod
    def get_current_wallpaper_path(cls) -> str:
        """Gets current desktop wallpaper path."""
        if sys.platform == "darwin":
            try:
                script = 'tell application "System Events" to get picture of current desktop'
                res = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception:
                pass
            return ""

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

    @classmethod
    def _set_startup_macos(cls, enable: bool) -> bool:
        plist_path = cls._get_macos_launch_agent_path()
        if not enable:
            try:
                if plist_path.exists():
                    plist_path.unlink()
                return True
            except Exception as e:
                print(f"Failed to remove macOS LaunchAgent: {e}")
                return False

        try:
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            if getattr(sys, "frozen", False):
                args = [sys.executable]
            else:
                args = [sys.executable, os.path.abspath(sys.argv[0])]

            args_xml = "\n".join(f"        <string>{arg}</string>" for arg in args)
            content = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                '<plist version="1.0">\n'
                '<dict>\n'
                f'    <key>Label</key>\n    <string>{APP_ID}</string>\n'
                f'    <key>ProgramArguments</key>\n    <array>\n{args_xml}\n    </array>\n'
                '    <key>RunAtLoad</key>\n    <true/>\n'
                '</dict>\n'
                '</plist>\n'
            )
            plist_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Failed to write macOS LaunchAgent: {e}")
            return False

    @classmethod
    def set_startup(cls, enable: bool) -> bool:
        """Sets application startup on boot (cross-platform)."""
        if sys.platform == "darwin":
            return cls._set_startup_macos(enable)
        if sys.platform != "win32" or winreg is None:
            return False

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
            )
            if enable:
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

    @classmethod
    def set_startup_with_windows(cls, enable: bool) -> bool:
        """Sets application startup on boot (compatible alias for existing callers)."""
        return cls.set_startup(enable)

    @classmethod
    def is_startup_enabled(cls) -> bool:
        """Checks if startup is enabled."""
        if sys.platform == "darwin":
            return cls._get_macos_launch_agent_path().exists()

        if sys.platform != "win32" or winreg is None:
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
