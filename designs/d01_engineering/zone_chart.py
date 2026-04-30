"""ZoneChart — heartbeat-style line that changes color per-segment by quality."""
from collections import deque
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore    import Qt, QRectF, QPointF
from PyQt5.QtGui     import (QPainter, QColor, QPen, QFont, QFontMetricsF)


# 3GPP-based quality zones — ascending threshold; the LAST zone is "best".
# format: (max_threshold, color_hex, label)
RSRP_ZONES = [
    (-110, "#7F1D1D", "Very Poor"),
    (-100, "#EA580C", "Poor"),
    (-90,  "#FACC15", "Fair"),
    (-80,  "#84CC16", "Good"),
    (-44,  "#10B981", "Excellent"),
]
RSRQ_ZONES = [
    (-19, "#7F1D1D", "Very Poor"),
    (-15, "#EA580C", "Poor"),
    (-12, "#FACC15", "Fair"),
    (-10, "#84CC16", "Good"),
    (-3,  "#10B981", "Excellent"),
]
SINR_ZONES = [
    (-5,  "#7F1D1D", "Very Poor"),
    (0,   "#EA580C", "Poor"),
    (10,  "#FACC15", "Fair"),
    (20,  "#84CC16", "Good"),
    (40,  "#10B981", "Excellent"),
]
RSSI_ZONES = [
    (-95, "#7F1D1D", "Very Poor"),
    (-85, "#EA580C", "Poor"),
    (-75, "#FACC15", "Fair"),
    (-65, "#84CC16", "Good"),
    (-30, "#10B981", "Excellent"),
]


def quality_for(value, zones):
    """Returns (label, color_hex) for the value's zone."""
    if value is None: return ("—", "#6B7280")
    for thr, color, label in zones:
        if value <= thr:
            return (label, color)
    return zones[-1][2], zones[-1][1]


class ZoneChart(QWidget):
    """Line chart whose color changes per-segment based on quality zones."""
    def __init__(self, name="", unit="", zones=None,
                 line_color="#FFFFFF", max_points=120, parent=None):
        super().__init__(parent)
        self.name       = name
        self.unit       = unit
        self.zones      = zones or RSRP_ZONES
        self.max_points = max_points
        self._buf       = deque(maxlen=max_points)
        self._last      = None
        # y-axis: lowest threshold to highest threshold
        thrs = [z[0] for z in self.zones]
        self._y_min = thrs[0]
        self._y_max = thrs[-1]
        self.setMinimumSize(220, 110)

    def addPoint(self, v):
        try:
            f = float(v)
        except Exception:
            return
        self._buf.append(f)
        self._last = f
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # outer card with a 1-px stroke so neighbouring charts don't bleed
        # together when the window is narrow.
        p.setPen(QPen(QColor(255, 255, 255, 35), 1))
        p.setBrush(QColor("#03070C"))
        p.drawRoundedRect(0, 0, w - 1, h - 1, 6, 6)

        # Tighter top/bottom padding when the chart is squeezed — keeps
        # title + axis labels readable on small windows.
        pl, pr = 38, 14
        if h < 100:
            pt, pb = 18, 10
        else:
            pt, pb = 26, 14
        cw = w - pl - pr
        ch = h - pt - pb
        y_range = self._y_max - self._y_min

        # ── Y-axis labels — drop the middle one when the chart is short
        # (it'd just visually collide with the top/bottom labels otherwise).
        ax_font = QFont("Consolas", 7)
        p.setFont(ax_font)
        p.setPen(QColor("#5A7BA0"))
        y_mid = (self._y_min + self._y_max) / 2
        thresholds = ((self._y_max, y_mid, self._y_min) if h >= 90
                       else (self._y_max, self._y_min))
        for thr in thresholds:
            y = pt + ch * (1.0 - (thr - self._y_min) / y_range)
            p.drawText(QRectF(0, y - 7, pl - 2, 14),
                       Qt.AlignRight|Qt.AlignVCenter, f"{thr:.0f}")
            p.setPen(QPen(QColor(255, 255, 255, 12), 1, Qt.DashLine))
            p.drawLine(pl, int(y), pl + cw, int(y))
            p.setPen(QColor("#5A7BA0"))

        # ── Title (top-left) ──
        ttl_font = QFont("Consolas", 9, QFont.Bold)
        p.setFont(ttl_font)
        p.setPen(QColor("#94B5D9"))
        p.drawText(QRectF(pl, 4, 80, 18),
                   Qt.AlignLeft|Qt.AlignVCenter, self.name.upper())

        # ── Current value + quality (top-right) ──
        if self._last is not None:
            val_text = f"{self._last:.0f}{self.unit}"
            q_label, q_color = quality_for(self._last, self.zones)
        else:
            val_text = f"—{self.unit}"
            q_label, q_color = ("—", "#6B7280")

        val_font = QFont("Consolas", 11, QFont.Bold)
        p.setFont(val_font)
        fm = QFontMetricsF(val_font)
        vw = fm.horizontalAdvance(val_text)
        p.setPen(QColor(q_color))
        p.drawText(QRectF(w - pr - vw, 4, vw, 18),
                   Qt.AlignRight|Qt.AlignVCenter, val_text)

        # quality label below value
        q_font = QFont("Segoe UI", 7, QFont.Bold)
        p.setFont(q_font)
        p.setPen(QColor(q_color))
        fm2 = QFontMetricsF(q_font)
        qw = fm2.horizontalAdvance(q_label)
        p.drawText(QRectF(w - pr - qw, h - 14, qw, 12),
                   Qt.AlignRight|Qt.AlignVCenter, q_label)

        # ── Plot the heartbeat line — per-segment color by quality ──
        if len(self._buf) >= 2:
            pts = list(self._buf)
            n = len(pts); n_max = self.max_points
            offset = n_max - n
            def to_pt(idx, v):
                vc = max(self._y_min, min(self._y_max, v))
                x = pl + cw * idx / max(1, n_max - 1)
                y = pt + ch * (1.0 - (vc - self._y_min) / y_range)
                return QPointF(x, y)

            # Draw each segment with its quality color
            prev_pt = to_pt(offset, pts[0])
            prev_v  = pts[0]
            for i in range(1, n):
                cur_v  = pts[i]
                cur_pt = to_pt(offset + i, cur_v)
                # color from average of two endpoints
                avg = (prev_v + cur_v) / 2
                _, seg_color = quality_for(avg, self.zones)
                col = QColor(seg_color)

                # glow under
                glow = QColor(col); glow.setAlpha(70)
                p.setPen(QPen(glow, 5, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(prev_pt, cur_pt)
                # main stroke
                p.setPen(QPen(col, 2.0, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(prev_pt, cur_pt)

                prev_pt = cur_pt
                prev_v  = cur_v

            # dot at last point with current quality color
            last_pt = to_pt(offset + n - 1, pts[-1])
            _, last_col = quality_for(pts[-1], self.zones)
            p.setPen(Qt.NoPen); p.setBrush(QColor(last_col))
            p.drawEllipse(last_pt, 3.5, 3.5)
            # small white core
            p.setBrush(QColor(255, 255, 255, 200))
            p.drawEllipse(last_pt, 1.5, 1.5)

        p.end()
