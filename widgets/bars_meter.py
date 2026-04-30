"""بار قياس أفقي مع label/value/colored fill."""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore    import Qt, QRectF
from PyQt5.QtGui     import QPainter, QColor, QFont, QFontMetricsF, QLinearGradient, QPen


class BarsMeter(QWidget):
    def __init__(self, label="", unit="%", min_val=0, max_val=100,
                 color=QColor(0, 212, 255), parent=None):
        super().__init__(parent)
        self.label = label
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.color = color
        self._value = 0
        self._sub = ""
        self.setMinimumHeight(58)

    def setValue(self, v, sub=""):
        try:
            self._value = float(v) if v is not None else 0
        except Exception:
            self._value = 0
        self._sub = sub
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # label + value row
        f1 = QFont("Segoe UI", 11, QFont.Bold)
        p.setFont(f1)
        p.setPen(QColor(110, 137, 172))
        p.drawText(QRectF(0, 0, w, 22), Qt.AlignLeft|Qt.AlignVCenter,
                   self.label.upper())

        # value
        f2 = QFont("Consolas", 14, QFont.Bold)
        p.setFont(f2)
        p.setPen(self.color)
        val_str = f"{self._value:.0f}{self.unit}"
        p.drawText(QRectF(0, 0, w-4, 22), Qt.AlignRight|Qt.AlignVCenter, val_str)

        # bar
        bar_y = 28
        bar_h = 12
        # bg
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(11, 18, 36))
        p.drawRoundedRect(QRectF(0, bar_y, w, bar_h), 6, 6)
        # fill
        ratio = max(0, min(1, (self._value - self.min_val) /
                            max(0.001, self.max_val - self.min_val)))
        if ratio > 0:
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0, self.color)
            grad.setColorAt(1, self.color.lighter(120))
            p.setBrush(grad)
            fill_w = max(6, w * ratio)
            p.drawRoundedRect(QRectF(0, bar_y, fill_w, bar_h), 6, 6)

        # sub
        if self._sub:
            p.setFont(QFont("Consolas", 10))
            p.setPen(QColor(74, 103, 136))
            p.drawText(QRectF(0, bar_y + bar_h + 2, w, 16),
                       Qt.AlignLeft|Qt.AlignVCenter, self._sub)
        p.end()
