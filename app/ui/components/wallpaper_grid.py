"""Scrollable grid for fixed-size wallpaper cards."""

from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QFrame, QScrollArea, QWidget

from .wallpaper_card import WallpaperCard


class WallpaperGrid(QScrollArea):
    spacing = 16
    vertical_margin = 4

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.cards: list[WallpaperCard] = []
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: transparent; border: none;")
        self.viewport().setStyleSheet("background: transparent; border: none;")
        self.content = QWidget()
        self.content.setStyleSheet("background: transparent; border: none;")
        self.setWidget(self.content)
        self._position_cards()

    def set_cards(self, cards: list[WallpaperCard]) -> None:
        for card in self.cards:
            card.hide()
            card.deleteLater()

        self.cards = cards
        self._position_cards()
        for card in self.cards:
            card.show()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._position_cards()

    def _position_cards(self) -> None:
        # The scroll area clips the content. Its viewport height must never
        # determine the row height, even during a resize or a refresh.
        horizontal_step = WallpaperCard.WIDTH + self.spacing
        vertical_step = WallpaperCard.HEIGHT + self.spacing
        viewport_width = self.viewport().width()
        columns = max(2, (viewport_width + self.spacing) // horizontal_step)
        rows = (len(self.cards) + columns - 1) // columns
        grid_width = max(0, min(columns, len(self.cards)) * horizontal_step - self.spacing)
        content_width = max(viewport_width, grid_width)
        content_height = max(0, rows * vertical_step - self.spacing) + 2 * self.vertical_margin
        left = (content_width - grid_width) // 2

        for index, card in enumerate(self.cards):
            row, column = divmod(index, columns)
            card.move(left + column * horizontal_step, self.vertical_margin + row * vertical_step)

        self.content.resize(content_width, content_height)
