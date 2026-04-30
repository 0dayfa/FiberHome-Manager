"""Circular gauge widget with glow arc."""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore    import Qt, QRectF
from PyQt5.QtGui     import (QPainter, QPen, QColor, QFont,
                              QFontMetricsF, QLinearGradient)
from typing import Optional


class CircularGauge(QWidget):
    """
    Stunning circular gauge.
    Arc spans 270° (bottom-left → bottom-right).
    Color interpolates: cyan → amber → red.
    """

    C_NORMAL = QColor(0,   212, 255)   # cyan
    C_WARN   = QColor(245, 158,  11)   # amber
    C_CRIT   = QColor(239,  68,  68)   # red
    C_TRACK  = QColor(20,  32,  50)
    C_BG     = QColor(11,  16,  30)

    def __init__(self, title: str = "", unit: str = "",
                 min_val: float = 0.0, max_val: float = 100.0,
                 warn_val: float = 70.0, crit_val: float = 90.0,
                 parent=None):
        super().__init__(parent)
        self.title    = title
        self.unit     = unit
        self.min_val  = min_val
        self.max_val  = max_val
        self.warn_val = warn_val
        self.crit_val = crit_val
        self._value: float = min_val
        self._text          = "—"
        self.setMinimumSize(150, 150)

    # ── public ───────────────────────────────────────────────────────

    def setValue(self, v: Optional[float]):
        if v is None:
            self._value = self.min_val
            self._text  = "—"
        else:
            self._value = max(self.min_val, min(self.max_val, float(v)))
            self._text  = f"{self._value:.0f}"
        self.update()

    # ── helpers ──────────────────────────────────────────────────────

    def _lerp_color(self, a: QColor, b: QColor, t: float) -> QColor:
        t = max(0.0, min(1.0, t))
        return QColor(
            int(a.red()   + (b.red()   - a.red())   * t),
            int(a.green() + (b.green() - a.green()) * t),
            int(a.blue()  + (b.blue()  - a.blue())  * t),
        )

    def _arc_color(self) -> QColor:
        if self._value >= self.crit_val:
            return self.C_CRIT
        if self._value >= self.warn_val:
            t = (self._value - self.warn_val) / max(1, self.crit_val - self.warn_val)
            return self._lerp_color(self.C_WARN, self.C_CRIT, t)
        t = (self._value - self.min_val) / max(1, self.warn_val - self.min_val)
        return self._lerp_color(self.C_NORMAL, self.C_WARN, t * 0.6)

    # ── paint ────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h   = self.width(), self.height()
        sz     = min(w, h) - 8
        ox     = (w - sz) / 2
        oy     = (h - sz) / 2
        outer  = QRectF(ox, oy, sz, sz)
        inset  = sz * 0.085
        arc_r  = outer.adjusted(inset, inset, -inset, -inset)

        # background fill
        p.setPen(Qt.NoPen)
        p.setBrush(self.C_BG)
        p.drawEllipse(outer)

        # outer glow ring
        pen = QPen(QColor(0, 212, 255, 18), 1.5)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(outer.adjusted(1, 1, -1, -1))

        # track arc
        START = 225
        SPAN  = 270
        p.setPen(QPen(self.C_TRACK, sz * 0.07, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc_r, START * 16, -SPAN * 16)

        # value arc
        ratio = (self._value - self.min_val) / max(0.001, self.max_val - self.min_val)
        color = self._arc_color()
        span  = int(-SPAN * 16 * ratio)

        # glow pass (wide, transparent)
        glow = QColor(color)
        glow.setAlpha(45)
        p.setPen(QPen(glow, sz * 0.14, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc_r, START * 16, span)

        # main arc
        p.setPen(QPen(color, sz * 0.075, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc_r, START * 16, span)

        # ── center text ──────────────────────────────────────────────
        cx, cy = w / 2.0, h / 2.0

        # value
        val_font = QFont("Consolas", max(8, int(sz * 0.18)), QFont.Bold)
        p.setFont(val_font)
        fm = QFontMetricsF(val_font)
        p.setPen(QColor(226, 232, 240))
        p.drawText(
            QRectF(ox, oy + sz * 0.20, sz, sz * 0.45),
            Qt.AlignCenter,
            self._text
        )

        # unit
        unit_font = QFont("Consolas", max(6, int(sz * 0.09)))
        p.setFont(unit_font)
        p.setPen(QColor(71, 85, 105))
        p.drawText(
            QRectF(ox, oy + sz * 0.52, sz, sz * 0.18),
            Qt.AlignCenter,
            self.unit
        )

        # title at bottom
        title_font = QFont("Segoe UI", max(6, int(sz * 0.085)))
        p.setFont(title_font)
        p.setPen(QColor(55, 75, 100))
        p.drawText(
            QRectF(ox, oy + sz * 0.78, sz, sz * 0.18),
            Qt.AlignCenter,
            self.title
        )

        p.end()
