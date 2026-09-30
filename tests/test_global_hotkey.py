"""Global wallpaper shortcut validation and settings behavior."""

import ctypes
import sys
from ctypes import wintypes

import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QWidget

from app.config import config
from app.constants import DEFAULT_NEXT_WALLPAPER_HOTKEY
from app.core.global_hotkey import GlobalHotkey, parse_hotkey
from app.ui.main_window import MainWindow


def test_default_shortcut_and_supported_combinations() -> None:
    assert DEFAULT_NEXT_WALLPAPER_HOTKEY == "Ctrl+Alt+N"
    assert parse_hotkey(DEFAULT_NEXT_WALLPAPER_HOTKEY) == (0x4003, ord("N"))
    assert parse_hotkey("Ctrl+Shift+F12") == (0x4006, 0x7B)
    assert parse_hotkey("Alt+Right") == (0x4001, 0x27)


@pytest.mark.parametrize("shortcut", ["", "N", "Shift+N", "Ctrl+;", "Ctrl+N, Ctrl+M"])
def test_invalid_shortcuts(shortcut: str) -> None:
    with pytest.raises(ValueError):
        parse_hotkey(shortcut)


def test_native_hotkey_dispatches_to_existing_switch_action() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    assert app is not None
    window = QWidget()
    calls = []
    hotkey = GlobalHotkey(window, lambda: calls.append(True))
    hotkey._enabled = True
    hotkey._hwnd = 1234
    message = wintypes.MSG()
    message.hWnd = 1234
    message.message = 0x0312
    message.wParam = 0x5357
    assert hotkey.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(message)) == (True, 0)
    assert calls == [True]
    hotkey._enabled = False


def test_settings_change_and_registration_failure(monkeypatch) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    assert app is not None
    monkeypatch.setitem(config._config, "next_wallpaper_hotkey", DEFAULT_NEXT_WALLPAPER_HOTKEY)
    monkeypatch.setattr(config, "save", lambda: None)
    monkeypatch.setattr("app.ui.main_window.GalleryPage.load_page", lambda _self, _page: None)

    class LightweightMainWindow(MainWindow):
        def _init_tray(self) -> None:
            pass

    window = LightweightMainWindow()
    page = window.settings_page
    assert page.next_hotkey_edit.keySequence().toString() == DEFAULT_NEXT_WALLPAPER_HOTKEY

    page.shortcut_change_requested.emit("Ctrl+Shift+F12")
    assert config.next_wallpaper_hotkey == "Ctrl+Shift+F12"
    assert window.global_hotkey.shortcut == "Ctrl+Shift+F12"

    monkeypatch.setattr(window.global_hotkey, "set_shortcut", lambda _shortcut: False)
    page.shortcut_change_requested.emit("Alt+Right")
    assert config.next_wallpaper_hotkey == "Ctrl+Shift+F12"
    assert page.next_hotkey_edit.keySequence() == QKeySequence("Ctrl+Shift+F12")
    assert page.hotkey_status.isVisibleTo(page)

    page.next_hotkey_edit.setKeySequence(QKeySequence("Shift+N"))
    page._on_hotkey_edited()
    assert config.next_wallpaper_hotkey == "Ctrl+Shift+F12"
    assert page.next_hotkey_edit.keySequence() == QKeySequence("Ctrl+Shift+F12")
    window.hide()
