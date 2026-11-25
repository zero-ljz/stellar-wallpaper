"""Qt application handling system quit requests."""

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication


class WallpaperApplication(QApplication):
    handling_quit = False

    def event(self, event: QEvent) -> bool:
        if event.type() != QEvent.Type.Quit:
            return super().event(event)
        previous = self.handling_quit
        self.handling_quit = True
        try:
            return super().event(event)
        finally:
            self.handling_quit = previous
