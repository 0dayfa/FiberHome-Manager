"""Circular usage gauge — green/yellow/orange/red based on threshold."""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore    import Qt, QRectF
from PyQt5.QtGui     import QPainter, QPen, QColor, QFont, QFontMetricsF


class UsageGauge(QWidget):
    """
    Circular gauge with color thresholds.
    thresholds: list[(threshold, color_hex)] sorted ascending.
    Default scale 0-100 (CPU/RAM %); for temperature pass max_v=100, label='°C'.
    """
    DEFAULT_THRESHOLDS = [
        (50, "#10B981"),   # green
        (70, "#FACC15"),   # yellow
        (85, "#F59E0B"),   # orange
        (101, "#EF4444"),  # red
    ]

    def __init__(self, title="", unit="%", min_v=0, max_v=100,
                 thresholds=None, parent=None):
        super().__init__(parent)
        self.title    = title
        self.unit     = unit
        self.min_v    = min_v
        self.max_v    = max_v
        self.thresh   = thresholds or self.DEFAULT_THRESHOLDS
        self._value: float | None = None
        self.setMinimumSize(140, 140)

    def setValue(self, v):
        try:
            self._value = float(v) if v not in (None, "") else None
        except Exception:
            self._value = None
        self.update()

    def _color_for(self, v) -> QColor:
        if v is None:
            return QColor("#9CA3AF")
        for thr, color in self.thresh:
            if v < thr:
                return QColor(color)
        return QColor(self.thresh[-1][1])

    def paintEvent(self, _e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        sz = min(w, h) - 14
        ox = (w - sz) / 2
        oy = (h - sz) / 2 - 4
        rect = QRectF(ox + sz*0.10, oy + sz*0.10, sz*0.80, sz*0.80)

        # bg circle
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#F0F0F0"))
        p.drawEllipse(QRectF(ox+2, oy+2, sz-4, sz-4))

        # outer thin ring
        p.setPen(QPen(QColor("#D8D8D8"), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(ox+1, oy+1, sz-2, sz-2))

        # arc track
        START = 225
        SPAN  = 270
        p.setPen(QPen(QColor("#E5E7EB"), sz*0.08, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, START*16, -SPAN*16)

        # value arc
        if self._value is not None:
            v = max(self.min_v, min(self.max_v, self._value))
            ratio = (v - self.min_v) / max(0.001, self.max_v - self.min_v)
            color = self._color_for(self._value)
            span = int(-SPAN*16 * ratio)
            # glow under
            glow = QColor(color); glow.setAlpha(60)
            p.setPen(QPen(glow, sz*0.13, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, START*16, span)
            # main arc
            p.setPen(QPen(color, sz*0.085, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, START*16, span)

        # title (top)
        title_font = QFont("Segoe UI", max(7, int(sz*0.085)), QFont.Bold)
        p.setFont(title_font)
        p.setPen(QColor("#666"))
        p.drawText(QRectF(ox, oy + sz*0.18, sz, sz*0.13),
                   Qt.AlignCenter, self.title.upper())

        # value (center)
        if self._value is None:
            val_text = "—"
        else:
            val_text = f"{self._value:.0f}"
        val_font = QFont("Consolas", max(11, int(sz*0.24)), QFont.Bold)
        p.setFont(val_font)
        p.setPen(QColor("#222"))
        p.drawText(QRectF(ox, oy + sz*0.34, sz, sz*0.30),
                   Qt.AlignCenter, val_text)

        # unit (below value)
        unit_font = QFont("Segoe UI", max(7, int(sz*0.10)), QFont.Bold)
        p.setFont(unit_font)
        p.setPen(self._color_for(self._value))
        p.drawText(QRectF(ox, oy + sz*0.62, sz, sz*0.16),
                   Qt.AlignCenter, self.unit)

        p.end()
