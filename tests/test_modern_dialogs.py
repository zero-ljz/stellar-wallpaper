"""Regression tests for component-library dialogs and message boxes."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from pyside6_modern_widgets import ModernDialog, ModernMessageBox

from app.ui.components import message_box
from app.ui.components.preview_dialog import PreviewDialog


def get_qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication(sys.argv)


def test_preview_uses_component_modern_dialog(monkeypatch) -> None:
    get_qapp()
    monkeypatch.setattr(PreviewDialog, "_load_image", lambda _self: None)

    dialog = PreviewDialog({"id": "42", "title": "测试壁纸"})

    assert isinstance(dialog, ModernDialog)
    assert dialog.windowTitle() == "壁纸高清大图预览"
    assert dialog._title_bar.titleLabel.text() == "壁纸高清大图预览"
    assert dialog._title_bar.isVisibleTo(dialog)
    assert dialog.layout().contentsMargins().top() == 5


def test_message_box_uses_component_buttons_and_chrome(tmp_path: Path) -> None:
    get_qapp()
    box, ok_button, cancel_button, open_button = message_box._create_message_box(
        None,
        "确认操作",
        "确定继续吗？",
        "question",
        ok_text="继续",
        cancel_text="返回",
        open_folder_path=tmp_path,
    )

    assert isinstance(box, ModernMessageBox)
    assert isinstance(box, QMessageBox)
    assert box.windowTitle() == "确认操作"
    assert box._title_bar.titleLabel.text() == "确认操作"
    assert box.text() == "确定继续吗？"
    assert ok_button.text() == "继续"
    assert cancel_button is not None and cancel_button.text() == "返回"
    assert open_button is not None and open_button.text() == "打开所在目录"
    assert box.defaultButton() is ok_button
    assert box.escapeButton() is cancel_button


def test_question_result_uses_clicked_custom_button(monkeypatch) -> None:
    get_qapp()

    def click_button_named(box: ModernMessageBox, text: str) -> int:
        next(button for button in box.buttons() if button.text() == text).click()
        return box.result()

    monkeypatch.setattr(
        ModernMessageBox,
        "exec",
        lambda box: click_button_named(box, "继续"),
    )
    assert message_box.show_question(None, "确认", "继续吗？", "继续", "取消")

    monkeypatch.setattr(
        ModernMessageBox,
        "exec",
        lambda box: click_button_named(box, "取消"),
    )
    assert not message_box.show_question(None, "确认", "继续吗？", "继续", "取消")


def test_save_message_open_folder_action(monkeypatch, tmp_path: Path) -> None:
    get_qapp()
    opened: list[Path | str] = []
    monkeypatch.setattr(message_box, "open_directory", opened.append)

    def click_open_folder(box: ModernMessageBox) -> int:
        next(
            button for button in box.buttons() if button.text() == "打开所在目录"
        ).click()
        return box.result()

    monkeypatch.setattr(ModernMessageBox, "exec", click_open_folder)
    target = tmp_path / "wallpaper.jpg"

    message_box.show_save_success(None, target)

    assert opened == [target.resolve()]


def test_message_box_buttons_have_explicit_contrast_styling_and_window_parenting(tmp_path: Path) -> None:
    get_qapp()
    from PySide6.QtWidgets import QWidget
    window = QWidget()
    child = QWidget(window)

    box, ok_button, cancel_button, open_button = message_box._create_message_box(
        child,
        "测试对比度",
        "消息文本",
        "success",
        ok_text="确定",
        cancel_text="取消",
        open_folder_path=tmp_path,
    )

    # Box should be parented to top-level window, not internal child
    assert box.parent() is window

    # Verify buttons have explicit styling with guaranteed contrast
    assert "#0078D4" in ok_button.styleSheet()
    assert "#FFFFFF" in ok_button.styleSheet()
    assert ok_button.cursor().shape() == Qt.CursorShape.PointingHandCursor

    assert open_button is not None
    assert "#0B0F19" in open_button.styleSheet()
    assert open_button.cursor().shape() == Qt.CursorShape.PointingHandCursor

    assert cancel_button is not None
    assert "#334155" in cancel_button.styleSheet()
    assert cancel_button.cursor().shape() == Qt.CursorShape.PointingHandCursor
    window.deleteLater()


def test_wallpaper_card_skips_duplicate_download(tmp_path: Path, monkeypatch) -> None:
    get_qapp()
    from app.config import config
    from app.ui.components.wallpaper_card import WallpaperCard
    from app.core.download_manager import build_download_target

    monkeypatch.setattr(config, "download_dir", str(tmp_path))
    monkeypatch.setattr(WallpaperCard, "_load_thumbnail", lambda _self: None)

    item = {"id": "test_dup", "download_url": "https://example.com/test_dup.jpg"}
    target = build_download_target(item, tmp_path)
    assert target is not None

    # Simulate existing downloaded file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"existing_content")

    downloaded_calls = []
    monkeypatch.setattr(
        "app.ui.components.wallpaper_card.download_wallpaper",
        lambda *args, **kwargs: downloaded_calls.append(True),
    )

    success_titles = []
    monkeypatch.setattr(
        "app.ui.components.wallpaper_card.show_save_success",
        lambda _parent, _path, title="保存成功": success_titles.append(title),
    )

    card = WallpaperCard(item)
    card.show()
    # Button should detect existing download immediately
    assert card.download_btn.toolTip() == "壁纸已保存到本地 (点击查看目录)"

    # Clicking should NOT trigger download_wallpaper
    card._on_download_clicked()
    assert downloaded_calls == []
    assert success_titles == ["壁纸已存在"]

    card.close()
    card.deleteLater()
