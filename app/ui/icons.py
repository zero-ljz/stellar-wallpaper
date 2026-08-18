"""Vector and programmatic QIcon generator for modern Windows 11 UI."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap


def create_icon(name: str, color: str = "#4B5563", size: int = 24) -> QIcon:
    """Generates clean vector-like QIcons for sidebar and actions."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    p_color = QColor(color)
    pen = QPen(p_color, 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    s = float(size)

    if name == "gallery":
        # Picture / Gallery icon
        rect = QRectF(s * 0.12, s * 0.15, s * 0.76, s * 0.7)
        painter.drawRoundedRect(rect, 3, 3)
        # Mountains
        path = QPainterPath()
        path.moveTo(s * 0.2, s * 0.72)
        path.lineTo(s * 0.45, s * 0.45)
        path.lineTo(s * 0.6, s * 0.6)
        path.lineTo(s * 0.72, s * 0.48)
        path.lineTo(s * 0.8, s * 0.72)
        painter.drawPath(path)
        # Sun
        painter.setBrush(p_color)
        painter.drawEllipse(QPointF(s * 0.35, s * 0.32), s * 0.07, s * 0.07)

    elif name == "shuffle":
        # Shuffle / Switch icon
        path = QPainterPath()
        path.moveTo(s * 0.15, s * 0.3)
        path.lineTo(s * 0.4, s * 0.3)
        path.lineTo(s * 0.65, s * 0.7)
        path.lineTo(s * 0.82, s * 0.7)
        painter.drawPath(path)
        # Arrow bottom
        painter.drawLine(QPointF(s * 0.72, s * 0.6), QPointF(s * 0.85, s * 0.7))
        painter.drawLine(QPointF(s * 0.72, s * 0.8), QPointF(s * 0.85, s * 0.7))

        path2 = QPainterPath()
        path2.moveTo(s * 0.15, s * 0.7)
        path2.lineTo(s * 0.4, s * 0.7)
        path2.lineTo(s * 0.65, s * 0.3)
        path2.lineTo(s * 0.82, s * 0.3)
        painter.drawPath(path2)
        # Arrow top
        painter.drawLine(QPointF(s * 0.72, s * 0.2), QPointF(s * 0.85, s * 0.3))
        painter.drawLine(QPointF(s * 0.72, s * 0.4), QPointF(s * 0.85, s * 0.3))

    elif name == "timer":
        # Clock / Timer icon
        painter.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.38, s * 0.38)
        painter.drawLine(QPointF(s * 0.5, s * 0.5), QPointF(s * 0.5, s * 0.24))
        painter.drawLine(QPointF(s * 0.5, s * 0.5), QPointF(s * 0.7, s * 0.5))

    elif name == "heart":
        # Heart / Favorite icon
        painter.setBrush(p_color)
        path = QPainterPath()
        path.moveTo(s * 0.5, s * 0.78)
        path.cubicTo(s * 0.15, s * 0.5, s * 0.12, s * 0.2, s * 0.32, s * 0.2)
        path.cubicTo(s * 0.42, s * 0.2, s * 0.48, s * 0.3, s * 0.5, s * 0.35)
        path.cubicTo(s * 0.52, s * 0.3, s * 0.58, s * 0.2, s * 0.68, s * 0.2)
        path.cubicTo(s * 0.88, s * 0.2, s * 0.85, s * 0.5, s * 0.5, s * 0.78)
        painter.drawPath(path)

    elif name == "history":
        # History / Clock-counterclockwise icon
        painter.drawArc(QRectF(s * 0.15, s * 0.15, s * 0.7, s * 0.7), 45 * 16, 270 * 16)
        painter.drawLine(QPointF(s * 0.5, s * 0.5), QPointF(s * 0.5, s * 0.28))
        painter.drawLine(QPointF(s * 0.5, s * 0.5), QPointF(s * 0.68, s * 0.5))
        # Arrow on arc
        painter.drawLine(QPointF(s * 0.65, s * 0.12), QPointF(s * 0.75, s * 0.22))
        painter.drawLine(QPointF(s * 0.85, s * 0.12), QPointF(s * 0.75, s * 0.22))

    elif name == "settings":
        # Gear / Settings icon
        painter.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.2, s * 0.2)
        for angle in range(0, 360, 45):
            painter.save()
            painter.translate(s * 0.5, s * 0.5)
            painter.rotate(angle)
            painter.drawLine(QPointF(0, -s * 0.28), QPointF(0, -s * 0.42))
            painter.restore()

    elif name == "refresh":
        painter.drawArc(QRectF(s * 0.18, s * 0.18, s * 0.64, s * 0.64), 30 * 16, 280 * 16)
        painter.drawLine(QPointF(s * 0.7, s * 0.15), QPointF(s * 0.82, s * 0.25))
        painter.drawLine(QPointF(s * 0.9, s * 0.15), QPointF(s * 0.82, s * 0.25))

    elif name == "search":
        painter.drawEllipse(QPointF(s * 0.4, s * 0.4), s * 0.25, s * 0.25)
        painter.drawLine(QPointF(s * 0.58, s * 0.58), QPointF(s * 0.82, s * 0.82))

    elif name == "folder":
        path = QPainterPath()
        path.moveTo(s * 0.15, s * 0.3)
        path.lineTo(s * 0.4, s * 0.3)
        path.lineTo(s * 0.48, s * 0.4)
        path.lineTo(s * 0.85, s * 0.4)
        path.lineTo(s * 0.85, s * 0.75)
        path.lineTo(s * 0.15, s * 0.75)
        path.closeSubpath()
        painter.drawPath(path)

    elif name == "download":
        painter.drawLine(QPointF(s * 0.5, s * 0.2), QPointF(s * 0.5, s * 0.65))
        painter.drawLine(QPointF(s * 0.3, s * 0.45), QPointF(s * 0.5, s * 0.65))
        painter.drawLine(QPointF(s * 0.7, s * 0.45), QPointF(s * 0.5, s * 0.65))
        painter.drawLine(QPointF(s * 0.2, s * 0.8), QPointF(s * 0.8, s * 0.8))

    else:
        # Generic dot
        painter.setBrush(p_color)
        painter.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.3, s * 0.3)

    painter.end()
    return QIcon(pixmap)
