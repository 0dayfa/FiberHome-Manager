"""Scientific signal quality meter - bar with red→orange→yellow→green gradient."""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore    import Qt, QRectF
from PyQt5.QtGui     import QPainter, QColor, QFont, QFontMetricsF, QLinearGradient, QPen


class QualityMeter(QWidget):
    """شريط أفقي مع تدرج لوني علمي + قيمة + label للجودة + scale ticks."""
    def __init__(self, title="RSRP", unit="dBm",
                  min_v=-140, max_v=-44,
                  zones=None,  # [(threshold, color), ...] sorted ascending
                  parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_v = min_v
        self.max_v = max_v
        # default zones for RSRP (descending quality with descending values)
        if zones is None:
            zones = [(-110, "#EF4444"), (-100, "#F97316"),
                     (-90, "#F59E0B"), (-80, "#22C55E"),
                     (-44, "#10B981")]
        self.zones = zones
        self._value = None
        self._quality = "—"
        self._quality_color = "#6E89AC"
        self.setMinimumHeight(96)

    def setValue(self, v, quality_label=None, quality_color=None):
        try:
            self._value = float(v) if v not in (None, "", "—") else None
        except Exception:
            self._value = None
        if quality_label is not None: self._quality = quality_label
        if quality_color is not None: self._quality_color = quality_color
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # Title
        f1 = QFont("Segoe UI", 10, QFont.Bold)
        p.setFont(f1)
        p.setPen(QColor(110, 137, 172))
        p.drawText(QRectF(0, 4, w, 18), Qt.AlignLeft|Qt.AlignVCenter, self.title.upper())
        # value (right side)
        val_str = f"{self._value:.0f} {self.unit}" if self._value is not None else f"— {self.unit}"
        f2 = QFont("Consolas", 14, QFont.Bold)
        p.setFont(f2)
        p.setPen(QColor(self._quality_color) if self._value is not None else QColor("#6E89AC"))
        p.drawText(QRectF(0, 4, w, 22), Qt.AlignRight|Qt.AlignVCenter, val_str)

        # quality label under value
        f3 = QFont("Segoe UI", 9, QFont.Bold)
        p.setFont(f3)
        p.setPen(QColor(self._quality_color))
        p.drawText(QRectF(0, 26, w, 16), Qt.AlignRight|Qt.AlignVCenter, self._quality)

        # Bar area
        bar_x = 0
        bar_y = 50
        bar_w = w
        bar_h = 14

        # gradient bar (red→orange→yellow→green)
        grad = QLinearGradient(0, 0, bar_w, 0)
        # split into evenly spaced color stops by zone thresholds (mapped 0..1)
        v_range = self.max_v - self.min_v
        stops = []
        for thr, color in self.zones:
            t = max(0, min(1, (thr - self.min_v) / v_range)) if v_range else 0
            stops.append((t, color))
        # ensure starts with first color at 0 and ends at 1
        if stops:
            if stops[0][0] > 0:
                stops.insert(0, (0, stops[0][1]))
            if stops[-1][0] < 1:
                stops.append((1, stops[-1][1]))
        for t, c in stops:
            grad.setColorAt(t, QColor(c))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 7, 7)

        # Mask non-active part with overlay
        if self._value is not None:
            v = max(self.min_v, min(self.max_v, self._value))
            t = (v - self.min_v) / v_range if v_range else 0
            indicator_x = bar_x + bar_w * t
            # vertical line indicator
            p.setPen(QPen(QColor(255, 255, 255, 230), 2))
            p.drawLine(int(indicator_x), bar_y - 4, int(indicator_x), bar_y + bar_h + 4)
            # circle marker
            p.setBrush(QColor(self._quality_color))
            p.setPen(QPen(QColor(255,255,255), 2))
            p.drawEllipse(QRectF(indicator_x - 6, bar_y + bar_h/2 - 6, 12, 12))

        # scale ticks (min, mid, max)
        p.setFont(QFont("Consolas", 8))
        p.setPen(QColor(74, 103, 136))
        ty = bar_y + bar_h + 4
        for i, val in enumerate([self.min_v, (self.min_v+self.max_v)/2, self.max_v]):
            tx = bar_x + bar_w * i / 2
            align = Qt.AlignLeft if i == 0 else (Qt.AlignRight if i == 2 else Qt.AlignHCenter)
            p.drawText(QRectF(max(0, tx - 30), ty, 60, 14), align, f"{val:.0f}")
        p.end()


# --- preset zones for common metrics ---
RSRP_ZONES = [(-110, "#EF4444"), (-100, "#F97316"),
              (-90, "#F59E0B"),  (-80, "#22C55E"), (-44, "#10B981")]
SINR_ZONES = [(-5, "#EF4444"),   (0,    "#F97316"),
              (13, "#F59E0B"),   (20,   "#22C55E"), (40, "#10B981")]
RSRQ_ZONES = [(-19, "#EF4444"),  (-17,  "#F97316"),
              (-15, "#F59E0B"),  (-10,  "#22C55E"), (-3, "#10B981")]
RSSI_ZONES = [(-95, "#EF4444"),  (-85,  "#F97316"),
              (-75, "#F59E0B"),  (-65,  "#22C55E"), (-30, "#10B981")]
