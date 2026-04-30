"""Signal meter — circular gauge مع تدرج لوني وعرض القيمة الكبيرة."""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore    import Qt, QRectF
from PyQt5.QtGui     import QPainter, QPen, QColor, QFont, QFontMetricsF


class SignalMeter(QWidget):
    """قياس RSRP/SINR/RSRQ على شكل قوس مع تدرج."""

    def __init__(self, title="", unit="", min_val=-140, max_val=-44,
                 warn_val=-100, crit_val=-115,
                 good_color=QColor(16, 185, 129),
                 warn_color=QColor(245, 158, 11),
                 crit_color=QColor(239, 68, 68),
                 invert=False,
                 parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.warn_val = warn_val
        self.crit_val = crit_val
        self.good_color = good_color
        self.warn_color = warn_color
        self.crit_color = crit_color
        self.invert = invert
        self._value = None
        self.setMinimumSize(180, 180)

    def setValue(self, v):
        if v is None or v == "":
            self._value = None
        else:
            try:
                self._value = float(v)
            except Exception:
                self._value = None
        self.update()

    def _color_for_value(self) -> QColor:
        if self._value is None:
            return QColor(60, 80, 110)
        if not self.invert:
            # higher = better (RSRP scale)
            if self._value >= self.warn_val:
                return self.good_color
            if self._value >= self.crit_val:
                return self.warn_color
            return self.crit_color
        else:
            if self._value <= self.warn_val:
                return self.good_color
            if self._value <= self.crit_val:
                return self.warn_color
            return self.crit_color

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        sz = min(w, h) - 8
        ox = (w - sz) / 2
        oy = (h - sz) / 2 - 4
        rect = QRectF(ox + sz*0.08, oy + sz*0.08, sz*0.84, sz*0.84)

        # background fill
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(8, 14, 28))
        p.drawEllipse(QRectF(ox+2, oy+2, sz-4, sz-4))

        # outer ring
        p.setPen(QPen(QColor(0, 212, 255, 30), 1))
        p.drawEllipse(QRectF(ox+1, oy+1, sz-2, sz-2))

        # track arc (270°)
        START = 225
        SPAN = 270
        p.setPen(QPen(QColor(20, 32, 54), sz*0.06, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, START*16, -SPAN*16)

        # value arc
        if self._value is not None:
            v = max(self.min_val, min(self.max_val, self._value))
            ratio = (v - self.min_val) / max(0.001, self.max_val - self.min_val)
            color = self._color_for_value()
            span = int(-SPAN*16 * ratio)
            # glow
            glow = QColor(color); glow.setAlpha(50)
            p.setPen(QPen(glow, sz*0.13, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, START*16, span)
            p.setPen(QPen(color, sz*0.07, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, START*16, span)

        # title (top inside)
        title_font = QFont("Segoe UI", max(8, int(sz*0.075)), QFont.Bold)
        p.setFont(title_font)
        p.setPen(QColor(110, 137, 172))
        p.drawText(QRectF(ox, oy + sz*0.18, sz, sz*0.12),
                   Qt.AlignCenter, self.title.upper())

        # value (center, big)
        val_text = "—" if self._value is None else f"{self._value:.0f}"
        val_font = QFont("Consolas", max(10, int(sz*0.20)), QFont.Bold)
        p.setFont(val_font)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(ox, oy + sz*0.34, sz, sz*0.30),
                   Qt.AlignCenter, val_text)

        # unit
        unit_font = QFont("Consolas", max(7, int(sz*0.085)))
        p.setFont(unit_font)
        p.setPen(QColor(74, 103, 136))
        p.drawText(QRectF(ox, oy + sz*0.62, sz, sz*0.16),
                   Qt.AlignCenter, self.unit)

        p.end()
