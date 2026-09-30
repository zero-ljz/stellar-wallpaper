"""Windows global shortcut for switching wallpapers while the window is hidden."""

from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QWidget

_HOTKEY_ID = 0x5357
_WM_HOTKEY = 0x0312
_MOD_ALT = 0x0001
_MOD_CONTROL = 0x0002
_MOD_SHIFT = 0x0004
_MOD_WIN = 0x0008
_MOD_NOREPEAT = 0x4000


def parse_hotkey(text: str) -> tuple[int, int]:
    """Return Win32 modifiers and virtual key for one supported key combination."""
    sequence = QKeySequence.fromString(text, QKeySequence.SequenceFormat.PortableText)
    if sequence.count() != 1:
        raise ValueError("请输入一个快捷键组合")

    combination = sequence[0]  # type: ignore[index]
    modifiers = combination.keyboardModifiers()
    if not modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier):
        raise ValueError("快捷键需包含 Ctrl、Alt 或 Win")

    key = combination.key()
    supported_keys = {
        Qt.Key.Key_Space: 0x20,
        Qt.Key.Key_PageUp: 0x21,
        Qt.Key.Key_PageDown: 0x22,
        Qt.Key.Key_End: 0x23,
        Qt.Key.Key_Home: 0x24,
        Qt.Key.Key_Left: 0x25,
        Qt.Key.Key_Up: 0x26,
        Qt.Key.Key_Right: 0x27,
        Qt.Key.Key_Down: 0x28,
        Qt.Key.Key_Insert: 0x2D,
        Qt.Key.Key_Delete: 0x2E,
    }
    if ord("A") <= key <= ord("Z") or ord("0") <= key <= ord("9"):
        virtual_key = key
    elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
        virtual_key = 0x70 + key - Qt.Key.Key_F1
    elif key in supported_keys:
        virtual_key = supported_keys[key]
    else:
        raise ValueError("请使用字母、数字、F1-F24 或常用导航键")

    flags = _MOD_NOREPEAT
    if modifiers & Qt.KeyboardModifier.AltModifier:
        flags |= _MOD_ALT
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        flags |= _MOD_CONTROL
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        flags |= _MOD_SHIFT
    if modifiers & Qt.KeyboardModifier.MetaModifier:
        flags |= _MOD_WIN
    return flags, virtual_key


class GlobalHotkey(QAbstractNativeEventFilter):
    def __init__(self, window: QWidget, callback: Callable[[], None]) -> None:
        super().__init__()
        self._window = window
        self._callback = callback
        self._shortcut = ""
        self._hwnd = 0
        self._hotkey_id = _HOTKEY_ID
        self._enabled = sys.platform == "win32" and QApplication.platformName() != "offscreen"
        if self._enabled:
            ctypes.windll.user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
            ctypes.windll.user32.RegisterHotKey.restype = wintypes.BOOL
            ctypes.windll.user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
            ctypes.windll.user32.UnregisterHotKey.restype = wintypes.BOOL
            app = QApplication.instance()
            if app is not None:
                app.installNativeEventFilter(self)

    @property
    def shortcut(self) -> str:
        return self._shortcut

    def set_shortcut(self, shortcut: str) -> bool:
        modifiers, key = parse_hotkey(shortcut)
        if shortcut == self._shortcut:
            return True
        if not self._enabled:
            self._shortcut = shortcut
            return True

        hwnd = int(self._window.winId())
        new_id = _HOTKEY_ID if not self._hwnd else _HOTKEY_ID + (self._hotkey_id == _HOTKEY_ID)
        if not ctypes.windll.user32.RegisterHotKey(hwnd, new_id, modifiers, key):
            return False

        if self._hwnd:
            ctypes.windll.user32.UnregisterHotKey(self._hwnd, self._hotkey_id)
        self._hwnd = hwnd
        self._hotkey_id = new_id
        self._shortcut = shortcut
        return True

    def nativeEventFilter(self, event_type, message):
        if self._enabled and event_type == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == _WM_HOTKEY and msg.hWnd == self._hwnd and msg.wParam == self._hotkey_id:
                self._callback()
                return True, 0
        return False, 0

    def close(self) -> None:
        if self._enabled:
            if self._hwnd:
                ctypes.windll.user32.UnregisterHotKey(self._hwnd, self._hotkey_id)
            app = QApplication.instance()
            if app is not None:
                app.removeNativeEventFilter(self)
        self._hwnd = 0
        self._shortcut = ""
