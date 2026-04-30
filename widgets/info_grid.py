"""Info grid — صفوف key/value بمحاذاة احترافية - بدون مربعات فارغة."""
from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy
from PyQt5.QtCore    import Qt


class InfoGrid(QFrame):
    """جدول 2-عمود (label : value) - يستخدم QGridLayout مع stretch صحيح."""

    def __init__(self, parent=None, label_width: int = 130):
        super().__init__(parent)
        self.setObjectName("card")
        self._lay = QGridLayout(self)
        self._lay.setContentsMargins(20, 16, 20, 16)
        self._lay.setHorizontalSpacing(16)
        self._lay.setVerticalSpacing(2)
        self._lay.setColumnMinimumWidth(0, label_width)
        self._lay.setColumnStretch(0, 0)
        self._lay.setColumnStretch(1, 1)
        self._row = 0
        self._labels: dict[str, QLabel] = {}

    def addTitle(self, text: str):
        lbl = QLabel(text.upper())
        lbl.setObjectName("section_title")
        self._lay.addWidget(lbl, self._row, 0, 1, 2)
        self._row += 1
        # divider line
        ln = QFrame(); ln.setFixedHeight(1)
        ln.setStyleSheet("background: #1A2845; margin: 4px 0px 8px 0px;")
        self._lay.addWidget(ln, self._row, 0, 1, 2)
        self._row += 1

    def add(self, key: str, fid: str | None = None,
            value: str = "—", value_color: str = "#BCD6F2"):
        k = QLabel(key)
        k.setStyleSheet("color:#6E89AC; font-size:13px; padding: 4px 0px;")
        k.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        v = QLabel(value)
        v.setStyleSheet(
            f"color:{value_color}; font-size:14px; font-family:Consolas; "
            "font-weight:bold; padding: 4px 0px;")
        v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._lay.addWidget(k, self._row, 0)
        self._lay.addWidget(v, self._row, 1)
        if fid:
            self._labels[fid] = v
        self._row += 1
        return v

    def addSeparator(self):
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#0F1A30; margin:6px 0px;")
        self._lay.addWidget(sep, self._row, 0, 1, 2)
        self._row += 1

    def addStretch(self):
        self._lay.setRowStretch(self._row, 1)
        self._row += 1

    def set(self, fid: str, value, color: str | None = None):
        lbl = self._labels.get(fid)
        if not lbl: return
        text = "—" if value is None or value == "" else str(value)
        lbl.setText(text)
        if color:
            lbl.setStyleSheet(
                f"color:{color}; font-size:14px; font-family:Consolas; "
                "font-weight:bold; padding: 4px 0px;")
