"""Windows 11 Fluent toggle switch component."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    Signal,
    Property,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget


class SwitchToggle(QAbstractButton):
    """Modern Windows 11 style animated toggle switch."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(44, 24)

        self._thumb_pos = 0.0  # 0.0 = left (unchecked), 1.0 = right (checked)

        self._anim = QPropertyAnimation(self, b"thumbPos", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.toggled.connect(self._on_toggled)

    def get_thumb_pos(self) -> float:
        return self._thumb_pos

    def set_thumb_pos(self, pos: float) -> None:
        self._thumb_pos = pos
        self.update()

    thumbPos = Property(float, get_thumb_pos, set_thumb_pos)

    def _on_toggled(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        super().setChecked(checked)
        self._thumb_pos = 1.0 if checked else 0.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        radius = h / 2.0

        # Background track color interpolation
        if self._thumb_pos >= 0.99:
            track_color = QColor("#0078D4")
            border_color = QColor("#0078D4")
        elif self._thumb_pos <= 0.01:
            track_color = QColor("#F1F5F9")
            border_color = QColor("#CBD5E1")
        else:
            # Interpolate
            t = self._thumb_pos
            r = int(241 + (0 - 241) * t)
            g = int(245 + (120 - 245) * t)
            b = int(249 + (212 - 249) * t)
            track_color = QColor(r, g, b)
            border_color = track_color

        # Draw track
        track_rect = QRectF(1, 1, w - 2, h - 2)
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, radius - 1, radius - 1)

        # Thumb circle
        thumb_diameter = h - 8.0
        min_x = 4.0
        max_x = w - thumb_diameter - 4.0
        cur_x = min_x + (max_x - min_x) * self._thumb_pos
        thumb_rect = QRectF(cur_x, 4.0, thumb_diameter, thumb_diameter)

        thumb_color = QColor("#FFFFFF") if self._thumb_pos > 0.1 else QColor("#64748B")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(thumb_color)
        painter.drawEllipse(thumb_rect)
