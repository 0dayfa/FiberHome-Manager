"""MultiLineChart — multiple lines on same canvas with auto-scale + legend."""
from collections import deque
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore    import Qt, QRectF, QPointF
from PyQt5.QtGui     import QPainter, QColor, QPen, QFont, QPainterPath, QBrush


class MultiLineChart(QWidget):
    """
    Multiple lines, each with own buffer + color.
    All lines share the same auto-scaled Y axis (so a single canvas).
    Top legend shows: name + current value with line color.
    """
    def __init__(self, title="", lines=None, max_points=120, parent=None):
        """
        lines: list[(name, color_hex, unit)]
        """
        super().__init__(parent)
        self.title = title
        self.max_points = max_points
        self.lines = lines or []
        self._bufs = {name: deque(maxlen=max_points) for name, _, _ in self.lines}
        self._last_values = {name: None for name, _, _ in self.lines}
        self.setMinimumSize(280, 200)

    def addPoint(self, name, value):
        if name not in self._bufs:
            return
        try:
            v = float(value)
        except Exception:
            return
        self._bufs[name].append(v)
        self._last_values[name] = v
        self.update()

    def addPoints(self, values: dict):
        """values: {name: value}"""
        for k, v in values.items():
            try:
                if v in (None, ""): continue
                self.addPoint(k, float(v))
            except Exception: pass

    def paintEvent(self, _e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#03070C"))
        p.drawRoundedRect(0, 0, w, h, 8, 8)

        # ── Title (top-left) ──
        title_font = QFont("Consolas", 10, QFont.Bold)
        p.setFont(title_font)
        p.setPen(QColor("#94A3B8"))
        p.drawText(QRectF(14, 8, 200, 18), Qt.AlignLeft|Qt.AlignVCenter,
                   self.title.upper())

        # ── Legend (top-right) ──
        leg_font = QFont("Consolas", 9, QFont.Bold)
        p.setFont(leg_font)
        leg_x = w - 14
        leg_y_top = 8
        # draw from right to left
        for name, color, unit in reversed(self.lines):
            v = self._last_values.get(name)
            txt = f"{name}: {v:.0f}{unit}" if v is not None else f"{name}: —{unit}"
            from PyQt5.QtGui import QFontMetricsF
            fm = QFontMetricsF(leg_font)
            tw = fm.horizontalAdvance(txt) + 8
            # color dot
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(color))
            p.drawEllipse(QRectF(leg_x - tw - 12, leg_y_top + 5, 8, 8))
            # text
            p.setPen(QColor(color))
            p.drawText(QRectF(leg_x - tw, leg_y_top, tw, 18),
                       Qt.AlignLeft|Qt.AlignVCenter, txt)
            leg_x -= tw + 16

        # ── Plot area ──
        pl, pr, pt, pb = 44, 14, 32, 18
        cw = w - pl - pr
        ch = h - pt - pb

        # Find global min/max across all buffers
        all_vals = []
        for buf in self._bufs.values():
            all_vals.extend(list(buf))
        if not all_vals:
            p.end()
            return
        y_min = min(all_vals)
        y_max = max(all_vals)
        if y_min == y_max:
            y_min -= 1; y_max += 1
        # margin
        margin = (y_max - y_min) * 0.10 + 0.5
        y_min -= margin; y_max += margin
        y_range = y_max - y_min

        # Grid
        p.setPen(QPen(QColor("#0D1A2C"), 1, Qt.DashLine))
        for i in range(1, 4):
            y = pt + ch * i / 3
            p.drawLine(pl, int(y), pl + cw, int(y))

        # Y-axis labels
        lab_font = QFont("Consolas", 8)
        p.setFont(lab_font)
        p.setPen(QColor("#5A7BA0"))
        for i in range(4):
            val = y_max - y_range * i / 3
            ypos = pt + ch * i / 3
            p.drawText(QRectF(0, ypos - 8, pl - 2, 16),
                       Qt.AlignRight|Qt.AlignVCenter, f"{val:.0f}")

        # Plot each line
        for name, color, _ in self.lines:
            buf = self._bufs.get(name)
            if not buf or len(buf) < 1: continue
            pts = list(buf)
            n = len(pts)
            n_max = self.max_points
            offset = n_max - n
            def to_pt(idx, v):
                x = pl + cw * idx / max(1, n_max - 1)
                y = pt + ch * (1.0 - (v - y_min) / y_range)
                return QPointF(x, y)
            path = QPainterPath()
            first = to_pt(offset, pts[0])
            path.moveTo(first)
            for i, v in enumerate(pts[1:], 1):
                path.lineTo(to_pt(offset + i, v))
            # glow
            glow = QColor(color); glow.setAlpha(40)
            p.setPen(QPen(glow, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(path)
            # main line
            p.setPen(QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(path)
            # dot at last
            last = to_pt(offset + n - 1, pts[-1])
            p.setPen(Qt.NoPen); p.setBrush(QColor(color))
            p.drawEllipse(last, 3, 3)

        # x-axis hint
        p.setFont(QFont("Consolas", 7))
        p.setPen(QColor("#3A5274"))
        p.drawText(QRectF(pl, pt + ch + 2, cw, 14), Qt.AlignRight, "live")
        p.end()
