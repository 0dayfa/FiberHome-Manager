"""Signal strength bars widget with RSRP label and quality tag."""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore    import Qt, QRectF
from PyQt5.QtGui     import QPainter, QColor, QFont, QFontMetricsF
from typing import Optional

_BAR_COLORS = {
    5: QColor(16, 185, 129),    # emerald
    4: QColor(34, 197, 148),
    3: QColor(245, 158,  11),   # amber
    2: QColor(249, 115,  22),   # orange
    1: QColor(239,  68,  68),   # red
    0: QColor(30,   40,  60),   # dim
}

_QUALITY_COLORS = {
    "Excellent": QColor(16,  185, 129),
    "Good":      QColor(34,  197, 148),
    "Fair":      QColor(245, 158,  11),
    "Poor":      QColor(249, 115,  22),
    "Very Poor": QColor(239,  68,  68),
    "N/A":       QColor(71,   85, 105),
}


class SignalBarsWidget(QWidget):
    def __init__(self, n_bars: int = 5, parent=None):
        super().__init__(parent)
        self.n_bars   = n_bars
        self._active  = 0
        self._rsrp: Optional[float] = None
        self._quality = "N/A"
        self._rat     = ""
        self.setMinimumSize(140, 120)

    def setSignal(self, bars: int, rsrp: Optional[float] = None,
                  quality: str = "N/A", rat: str = ""):
        self._active  = max(0, min(self.n_bars, bars))
        self._rsrp    = rsrp
        self._quality = quality
        self._rat     = rat
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h     = float(self.width()), float(self.height())
        n        = self.n_bars
        gap      = max(3.0, w * 0.04)
        bar_w    = max(8.0, (w * 0.80 - gap * (n - 1)) / n)
        max_h    = h * 0.48
        bottom_y = h * 0.62
        start_x  = (w - (n * bar_w + (n - 1) * gap)) / 2.0

        active_color = _BAR_COLORS.get(self._active, _BAR_COLORS[0])
        dim_color    = _BAR_COLORS[0]

        for i in range(n):
            bar_h = max_h * (i + 1) / n
            x     = start_x + i * (bar_w + gap)
            y     = bottom_y - bar_h
            color = active_color if i < self._active else dim_color
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            rad = bar_w * 0.25
            p.drawRoundedRect(QRectF(x, y, bar_w, bar_h), rad, rad)

        # RSRP
        rsrp_str = f"{self._rsrp:.0f} dBm" if self._rsrp is not None else "— dBm"
        f1 = QFont("Consolas", 11, QFont.Bold)
        p.setFont(f1)
        p.setPen(QColor(200, 220, 240))
        fm1 = QFontMetricsF(f1)
        tw  = fm1.horizontalAdvance(rsrp_str)
        p.drawText(QRectF((w - tw) / 2, bottom_y + 4, tw + 2, 20),
                   Qt.AlignLeft, rsrp_str)

        # Quality
        f2 = QFont("Segoe UI", 10, QFont.Bold)
        p.setFont(f2)
        q_color = _QUALITY_COLORS.get(self._quality, _QUALITY_COLORS["N/A"])
        p.setPen(q_color)
        fm2 = QFontMetricsF(f2)
        qw  = fm2.horizontalAdvance(self._quality)
        p.drawText(QRectF((w - qw) / 2, bottom_y + 24, qw + 2, 18),
                   Qt.AlignLeft, self._quality)

        # RAT label (LTE / 5G)
        if self._rat:
            f3 = QFont("Consolas", 9, QFont.Bold)
            p.setFont(f3)
            p.setPen(QColor(0, 212, 255, 220))
            fm3 = QFontMetricsF(f3)
            rw  = fm3.horizontalAdvance(self._rat)
            p.drawText(QRectF((w - rw) / 2, bottom_y + 42, rw + 2, 16),
                       Qt.AlignLeft, self._rat)

        p.end()
