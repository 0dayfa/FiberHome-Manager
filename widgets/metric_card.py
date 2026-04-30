"""Premium metric card — title, big value, unit, trend hint."""
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore    import Qt
from PyQt5.QtGui     import QFont


class MetricCard(QFrame):
    def __init__(self, label: str, unit: str = "", color: str = "#00D4FF",
                 hint: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._color = color
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(2)

        top = QHBoxLayout()
        self._label = QLabel(label.upper())
        self._label.setStyleSheet(
            "color:#6E89AC; font-size:11px; letter-spacing:2px; font-weight:bold;")
        top.addWidget(self._label)
        top.addStretch()
        self._chip = QLabel("")
        self._chip.setStyleSheet(f"color:{color}; font-size:10px; font-weight:bold;")
        top.addWidget(self._chip)
        lay.addLayout(top)

        row = QHBoxLayout()
        row.setSpacing(4)
        self._val = QLabel("—")
        self._val.setStyleSheet(
            f"color:{color}; font-size:36px; font-family:Consolas; font-weight:800;")
        row.addWidget(self._val)
        self._unit = QLabel(unit)
        self._unit.setStyleSheet("color:#4A6788; font-size:14px; padding-bottom:6px;")
        row.addWidget(self._unit)
        row.addStretch()
        lay.addLayout(row)

        self._hint = QLabel(hint)
        self._hint.setStyleSheet("color:#4A6788; font-size:11px;")
        lay.addWidget(self._hint)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(110)

    def setValue(self, val, hint: str | None = None, color: str | None = None):
        self._val.setText("—" if val is None or val == "" else str(val))
        if color:
            self._val.setStyleSheet(
                f"color:{color}; font-size:36px; font-family:Consolas; font-weight:800;")
        if hint is not None:
            self._hint.setText(hint)

    def setChip(self, text: str, color: str | None = None):
        self._chip.setText(text)
        if color:
            self._chip.setStyleSheet(f"color:{color}; font-size:10px; font-weight:bold;")
