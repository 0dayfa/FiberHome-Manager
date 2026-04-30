"""Scrolling real-time line chart drawn with QPainter."""

from collections import deque
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore    import Qt, QRectF, QPointF
from PyQt5.QtGui     import (QPainter, QColor, QPen,
                              QPainterPath, QLinearGradient, QBrush, QFont)


class LiveChart(QWidget):
    """
    Scrolling chart that accepts addPoint() calls.
    Draws a gradient fill + anti-aliased line + glow dot at latest value.
    """

    def __init__(self, title: str = "", unit: str = "",
                 color: QColor = None, max_points: int = 60,
                 parent=None):
        super().__init__(parent)
        self.title      = title
        self.unit       = unit
        self.color      = color or QColor(0, 212, 255)
        self.max_points = max_points
        self._buf       = deque(maxlen=max_points)
        self._y_min     = 0.0
        self._y_max     = 1.0
        self.setMinimumSize(200, 80)

    def addPoint(self, value: float):
        self._buf.append(float(value))
        if self._buf:
            hi = max(self._buf)
            lo = min(self._buf)
            self._y_max = hi * 1.15 + 1
            self._y_min = max(0.0, lo * 0.85)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h   = self.width(), self.height()
        pl, pr = 38, 10
        pt, pb = 8,  24
        cw     = w - pl - pr
        ch     = h - pt - pb

        # background
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(5, 8, 16))
        p.drawRoundedRect(0, 0, w, h, 8, 8)

        # grid
        grid_pen = QPen(QColor(18, 28, 44), 1, Qt.DashLine)
        p.setPen(grid_pen)
        y_range = max(0.001, self._y_max - self._y_min)
        for i in range(1, 4):
            y = pt + ch * i / 3
            p.drawLine(pl, int(y), pl + cw, int(y))

        # y-axis labels
        lab_font = QFont("Consolas", 9)
        p.setFont(lab_font)
        p.setPen(QColor(90, 120, 160))
        for i in range(4):
            val  = self._y_max - y_range * i / 3
            ypos = pt + ch * i / 3
            p.drawText(QRectF(0, ypos - 8, pl - 2, 16),
                       Qt.AlignRight | Qt.AlignVCenter,
                       f"{val:.0f}")

        if len(self._buf) < 2:
            p.end()
            return

        pts   = list(self._buf)
        n     = len(pts)
        n_max = self.max_points

        def to_pt(idx: int, v: float) -> QPointF:
            x = pl + cw * idx / (n_max - 1)
            y = pt + ch * (1.0 - (v - self._y_min) / y_range)
            return QPointF(x, y)

        offset = n_max - n
        first  = to_pt(offset, pts[0])

        path = QPainterPath()
        path.moveTo(first)
        for i, v in enumerate(pts[1:], 1):
            path.lineTo(to_pt(offset + i, v))

        last = to_pt(offset + n - 1, pts[-1])

        # gradient fill
        fill = QPainterPath(path)
        fill.lineTo(last.x(), pt + ch)
        fill.lineTo(first.x(), pt + ch)
        fill.closeSubpath()

        grad = QLinearGradient(0, pt, 0, pt + ch)
        grad.setColorAt(0.0, QColor(self.color.red(), self.color.green(),
                                    self.color.blue(), 90))
        grad.setColorAt(1.0, QColor(self.color.red(), self.color.green(),
                                    self.color.blue(), 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawPath(fill)

        # glow line pass
        glow = QColor(self.color)
        glow.setAlpha(40)
        p.setPen(QPen(glow, 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # main line
        p.setPen(QPen(self.color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)

        # dot at latest point
        p.setPen(Qt.NoPen)
        p.setBrush(self.color)
        p.drawEllipse(last, 4, 4)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(last, 2, 2)

        # title + current
        cur_str = f"{pts[-1]:.1f} {self.unit}"
        t_font  = QFont("Consolas", 10, QFont.Bold)
        p.setFont(t_font)
        p.setPen(self.color)
        p.drawText(QRectF(pl + 4, pt + 2, cw - 8, 16),
                   Qt.AlignLeft, f"{self.title}   {cur_str}")

        # x-axis hint
        p.setFont(QFont("Consolas", 9))
        p.setPen(QColor(70, 100, 130))
        p.drawText(QRectF(pl, pt + ch + 4, cw, 16),
                   Qt.AlignRight, "live")

        p.end()
