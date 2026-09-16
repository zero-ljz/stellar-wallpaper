"""Regression coverage for clicks on the card's hover actions."""

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QEnterEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.ui.components.wallpaper_card import WallpaperCard


def enter_card(card):
    center = card.rect().center()
    QApplication.sendEvent(
        card,
        QEnterEvent(QPointF(center), QPointF(center), QPointF(card.mapToGlobal(center))),
    )


@pytest.fixture
def card(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(WallpaperCard, "_load_thumbnail", lambda _self: None)
    monkeypatch.setattr(
        "app.ui.components.wallpaper_card.db.is_favorite", lambda *_args: False
    )
    widget = WallpaperCard({"id": "42"})
    widget.show()
    app.processEvents()
    enter_card(widget)
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("button_name", ["apply_btn", "preview_btn"])
def test_action_click_survives_leaving_and_reentering_card(card, button_name):
    requested = []
    previews = []
    card.apply_requested.connect(lambda item: requested.append(item))
    card.preview_requested.connect(lambda item: previews.append(item))
    button = getattr(card, button_name)

    QTest.mousePress(button, Qt.MouseButton.LeftButton)
    QApplication.sendEvent(card, QEvent(QEvent.Type.Leave))
    QTest.qWait(160)

    assert not card.action_row_widget.isHidden()
    assert button.isDown()
    enter_card(card)
    QTest.mouseRelease(button, Qt.MouseButton.LeftButton)

    assert requested == ([card.item_data] if button_name == "apply_btn" else [])
    assert previews == ([card.item_data] if button_name == "preview_btn" else [])


def test_releasing_outside_action_does_not_apply_wallpaper(card):
    requested = []
    card.apply_requested.connect(requested.append)
    QTest.mousePress(card.apply_btn, Qt.MouseButton.LeftButton)
    QApplication.sendEvent(card, QEvent(QEvent.Type.Leave))
    QTest.mouseRelease(card.apply_btn, Qt.MouseButton.LeftButton, pos=QPoint(-10, -10))
    QTest.qWait(160)

    assert requested == []
    assert card.action_row_widget.isHidden()


def test_hover_actions_return_after_leaving_selection_mode(card):
    card.set_selection_mode(True)
    assert card.action_row_widget.isHidden()

    card.set_selection_mode(False)
    assert not card.action_row_widget.isHidden()


def test_hover_does_not_move_action_buttons(card):
    before = card.apply_btn.mapTo(card, QPoint())
    QApplication.sendEvent(card, QEvent(QEvent.Type.Leave))
    QTest.qWait(160)
    assert card.action_row_widget.isHidden()
    assert card.apply_btn.mapTo(card, QPoint()) == before

    enter_card(card)
    QApplication.processEvents()
    assert card.apply_btn.mapTo(card, QPoint()) == before
