"""Draw etime's icon (app/icon.png, 1024x1024) in the overlay's warm-paper palette.

A stopwatch with a gold wedge for time elapsed, on a cream rounded square sized
to macOS's icon grid (824px body on a 1024px canvas). Run from the repo root:

    .venv/bin/python app/make_icon.py
"""

from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen

BROWN = QColor("#7A5230")     # the dashboard favicon's hand color
GOLD = QColor("#D9A441")      # COLOR_RECENT
GOLD_FILL = QColor("#EFD39A")
CREAM_TOP = QColor("#F8F3EA")
CREAM_BOTTOM = QColor("#EADFCB")
EDGE = QColor("#D2C3A8")

SIZE = 1024
OUT = Path(__file__).with_name("icon.png")


def draw() -> QImage:
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Soft shadow under the body, then the body itself.
    body = QRectF(100, 100, 824, 824)
    for i, alpha in enumerate([10, 8, 6, 4]):
        shadow = QPainterPath()
        shadow.addRoundedRect(body.adjusted(-i * 3, 6 + i * 4, i * 3, 8 + i * 5), 185, 185)
        p.fillPath(shadow, QColor(60, 40, 20, alpha))
    path = QPainterPath()
    path.addRoundedRect(body, 185, 185)
    grad = QLinearGradient(0, body.top(), 0, body.bottom())
    grad.setColorAt(0, CREAM_TOP)
    grad.setColorAt(1, CREAM_BOTTOM)
    p.fillPath(path, QBrush(grad))
    p.setPen(QPen(EDGE, 4))
    p.drawPath(path)

    center = QPointF(512, 548)
    r = 262

    # Crown: the stopwatch button on top.
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(BROWN)
    p.drawRoundedRect(QRectF(492, center.y() - r - 62, 40, 70), 10, 10)
    p.drawRoundedRect(QRectF(452, center.y() - r - 100, 120, 48), 20, 20)

    # Elapsed wedge from 12 o'clock clockwise to the hand (Qt angles: 1/16°,
    # counter-clockwise from 3 o'clock, so 12 o'clock is 90° and clockwise is negative).
    sweep = 130
    p.setBrush(GOLD_FILL)
    inner = r - 20  # tucked under the ring stroke (40px wide) so no gap shows
    p.drawPie(QRectF(center.x() - inner, center.y() - inner, 2 * inner, 2 * inner), 90 * 16, -sweep * 16)

    # Face ring.
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(BROWN, 40))
    p.drawEllipse(center, r, r)

    # Hand, at the wedge's leading edge.
    from math import cos, radians, sin
    angle = radians(90 - sweep)
    tip = QPointF(center.x() + (r - 70) * cos(angle), center.y() - (r - 70) * sin(angle))
    pen = QPen(BROWN, 34)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(center, tip)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(BROWN)
    p.drawEllipse(center, 30, 30)
    p.setBrush(GOLD)
    p.drawEllipse(center, 12, 12)

    p.end()
    return img


if __name__ == "__main__":
    app = QGuiApplication([])
    draw().save(str(OUT))
    print(f"Wrote {OUT}")
