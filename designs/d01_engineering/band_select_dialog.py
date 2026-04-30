"""Band Select dialog — view/lock LTE & NR bands."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QFrame, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui  import QColor, QFont
import router_api as rapi


STYLE = """
QDialog { background:#ECEFF1; }
QFrame#hdr {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0D47A1, stop:1 #1565C0);
    border:none; }
QLabel#hdrtitle {
    color:#FFFFFF; font-size:20px; font-weight:bold;
    padding:16px 24px 0px 24px; letter-spacing:3px; }
QLabel#hdrsub {
    color:rgba(255,255,255,0.78); font-size:11px;
    padding:0 24px 16px 24px; letter-spacing:1px; }
QFrame#card { background:#FFFFFF; border:1px solid #D5D8DD; border-radius:6px; }
QLabel#sectitle {
    color:#37474F; font-size:12px; font-weight:bold; letter-spacing:3px; }
QLabel#kk { color:#607D8B; font-size:12px; }
QLabel#vv { color:#212121; font-size:13px; font-family:Consolas; font-weight:bold; }
QLabel#statusOn  {
    color:#1B5E20; font-weight:bold; font-size:13px;
    padding:5px 16px; background:#C8E6C9;
    border:1px solid #66BB6A; border-radius:14px; letter-spacing:1px; }
QLabel#statusOff {
    color:#616161; font-weight:bold; font-size:13px;
    padding:5px 16px; background:#ECEFF1;
    border:1px solid #B0BEC5; border-radius:14px; letter-spacing:1px; }
QPushButton {
    background:#FFFFFF; border:1px solid #B0BEC5; border-radius:4px;
    padding:8px 22px; font-size:13px; font-weight:bold; color:#37474F;
    min-width:110px; }
QPushButton:hover { background:#ECEFF1; border-color:#78909C; }
QPushButton#apply {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1565C0, stop:1 #0D47A1);
    color:#FFFFFF; border:none; }
QPushButton#apply:hover { background:#0D47A1; }
QPushButton#disable {
    background:#C62828; color:#FFFFFF; border:none; }
QPushButton#disable:hover { background:#B71C1C; }
"""


# Custom band chip with toggle behavior
class _BandChip(QFrame):
    toggled = pyqtSignal()
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self._checked = False
        self._label = label
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        l = QVBoxLayout(self); l.setContentsMargins(0,0,0,0); l.setSpacing(0)
        self._lbl = QLabel(label)
        self._lbl.setAlignment(Qt.AlignCenter)
        l.addWidget(self._lbl)
        self._update_style()

    def setChecked(self, v):
        self._checked = bool(v)
        self._update_style()

    def isChecked(self):
        return self._checked

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._checked = not self._checked
            self._update_style()
            self.toggled.emit()

    def _update_style(self):
        if self._checked:
            self.setStyleSheet(
                "QFrame { background:#1565C0; border:1.5px solid #0D47A1; "
                "border-radius:6px; }")
            self._lbl.setStyleSheet(
                "color:#FFFFFF; font-size:14px; font-family:Consolas; font-weight:bold;")
        else:
            self.setStyleSheet(
                "QFrame { background:#FFFFFF; border:1.5px solid #B0BEC5; "
                "border-radius:6px; }")
            self._lbl.setStyleSheet(
                "color:#37474F; font-size:14px; font-family:Consolas; font-weight:bold;")


class BandSelectDialog(QDialog):
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.setWindowTitle("Band Select")
        self.setStyleSheet(STYLE)
        self.setMinimumSize(760, 660)
        self._build_ui()
        QTimer.singleShot(150, self._refresh)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # ── Header banner ──
        hdr = QFrame(); hdr.setObjectName("hdr")
        hl = QVBoxLayout(hdr); hl.setContentsMargins(0,0,0,0); hl.setSpacing(0)
        t = QLabel("⚙  BAND SELECT  ·  FREQUENCY LOCK")
        t.setObjectName("hdrtitle")
        hl.addWidget(t)
        sub = QLabel("Pin the modem to specific 4G LTE / 5G NR bands  ·  "
                      "Modem will briefly reset on apply")
        sub.setObjectName("hdrsub")
        hl.addWidget(sub)
        root.addWidget(hdr)

        # ── Body ──
        body = QVBoxLayout()
        body.setContentsMargins(20, 16, 20, 16); body.setSpacing(14)

        # Status card
        status_card = QFrame(); status_card.setObjectName("card")
        sl = QVBoxLayout(status_card); sl.setContentsMargins(20, 14, 20, 14); sl.setSpacing(10)
        st_row = QHBoxLayout()
        lbl = QLabel("CURRENT LOCK STATUS"); lbl.setObjectName("sectitle")
        st_row.addWidget(lbl)
        st_row.addStretch()
        self.status_chip = QLabel("● —"); self.status_chip.setObjectName("statusOff")
        st_row.addWidget(self.status_chip)
        sl.addLayout(st_row)

        info = QGridLayout(); info.setHorizontalSpacing(20); info.setVerticalSpacing(6)
        items = [("LTE Locked Bands", "lte_now"),
                 ("NR  Locked Bands", "nr_now"),
                 ("Cell Lock", "cell_lock"),
                 ("Airplane Mode", "airplane")]
        for i, (lbl, fid) in enumerate(items):
            kk = QLabel(lbl); kk.setObjectName("kk")
            vv = QLabel("—"); vv.setObjectName("vv")
            info.addWidget(kk, i, 0)
            info.addWidget(vv, i, 1)
            setattr(self, f"_v_{fid}", vv)
        info.setColumnStretch(1, 1)
        sl.addLayout(info)
        body.addWidget(status_card)

        # ── LTE Bands ──
        lte_card = QFrame(); lte_card.setObjectName("card")
        ll = QVBoxLayout(lte_card); ll.setContentsMargins(20, 14, 20, 14); ll.setSpacing(10)
        lt = QLabel(f"4G LTE BANDS  ·  {len(rapi.LTE_BANDS)} SUPPORTED")
        lt.setObjectName("sectitle")
        ll.addWidget(lt)
        lt_grid = QGridLayout(); lt_grid.setHorizontalSpacing(8); lt_grid.setVerticalSpacing(8)
        self.cb_lte = {}
        for i, b in enumerate(rapi.LTE_BANDS):
            chip = _BandChip(f"B{b}")
            self.cb_lte[b] = chip
            lt_grid.addWidget(chip, i // 7, i % 7)
        ll.addLayout(lt_grid)
        body.addWidget(lte_card)

        # ── NR Bands ──
        nr_card = QFrame(); nr_card.setObjectName("card")
        nl = QVBoxLayout(nr_card); nl.setContentsMargins(20, 14, 20, 14); nl.setSpacing(10)
        nt = QLabel(f"5G NR BANDS  ·  {len(rapi.NR_BANDS)} SUPPORTED")
        nt.setObjectName("sectitle")
        nl.addWidget(nt)
        nr_grid = QGridLayout(); nr_grid.setHorizontalSpacing(8); nr_grid.setVerticalSpacing(8)
        self.cb_nr = {}
        for i, b in enumerate(rapi.NR_BANDS):
            chip = _BandChip(f"N{b}")
            self.cb_nr[b] = chip
            nr_grid.addWidget(chip, i // 7, i % 7)
        nl.addLayout(nr_grid)
        body.addWidget(nr_card)

        # ── Footer buttons ──
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_clear = QPushButton("Clear All"); btn_clear.clicked.connect(self._clear)
        btn_refresh = QPushButton("Refresh"); btn_refresh.clicked.connect(self._refresh)
        btn_disable = QPushButton("Disable Lock"); btn_disable.setObjectName("disable")
        btn_disable.clicked.connect(self._disable)
        btn_apply = QPushButton("Apply & Enable Lock"); btn_apply.setObjectName("apply")
        btn_apply.clicked.connect(self._apply)
        btn_close = QPushButton("Close"); btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_refresh); btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        btn_row.addWidget(btn_disable); btn_row.addWidget(btn_apply); btn_row.addWidget(btn_close)
        body.addLayout(btn_row)

        root.addLayout(body)

    def _refresh(self):
        try:
            d = rapi.get_band_lock(self.client)
            self._apply_state(d)
        except Exception as e:
            self.status_chip.setText("● ERROR")
            QMessageBox.warning(self, "Refresh Error",
                f"Could not read current band lock state:\n{e}")

    def _apply_state(self, d):
        en = d.get("enable", False)
        if en:
            self.status_chip.setText("● ENABLED")
            self.status_chip.setObjectName("statusOn")
        else:
            self.status_chip.setText("● DISABLED")
            self.status_chip.setObjectName("statusOff")
        self.status_chip.style().unpolish(self.status_chip)
        self.status_chip.style().polish(self.status_chip)
        self.status_chip.update()

        lte = [b for b in (d.get("lte_locked","") or "").split(",") if b]
        nr  = [b for b in (d.get("nr_locked","")  or "").split(",") if b]

        for b, chip in self.cb_lte.items(): chip.setChecked(b in lte)
        for b, chip in self.cb_nr.items():  chip.setChecked(b in nr)

        self._v_lte_now.setText(", ".join(f"B{b}" for b in lte) if lte else "—")
        self._v_nr_now.setText(", ".join(f"N{b}" for b in nr) if nr else "—")
        self._v_cell_lock.setText("ENABLED" if d.get("cell_lock_enable") else "Disabled")
        self._v_airplane.setText("ON" if d.get("airplane") else "Off")

    def _selected_lte(self):
        return [b for b, c in self.cb_lte.items() if c.isChecked()]

    def _selected_nr(self):
        return [b for b, c in self.cb_nr.items() if c.isChecked()]

    def _clear(self):
        for c in list(self.cb_lte.values()) + list(self.cb_nr.values()):
            c.setChecked(False)

    def _apply(self):
        lte = self._selected_lte()
        nr  = self._selected_nr()
        if not lte and not nr:
            QMessageBox.warning(self, "No Selection",
                "Select at least one band before applying.")
            return
        msg = (
            f"Enable Band Lock with:\n\n"
            f"  4G LTE: {', '.join('B'+b for b in lte) if lte else '— (none)'}\n"
            f"  5G NR : {', '.join('N'+b for b in nr) if nr else '— (none)'}\n\n"
            f"⚠  The modem will reset and the connection will drop briefly.")
        if QMessageBox.question(self, "Confirm Band Lock", msg,
                                  QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            rapi.set_band_lock(self.client, True, lte_bands=lte, nr_bands=nr)
            QMessageBox.information(self, "Applied",
                "Band Lock applied. Modem is reconnecting…")
            QTimer.singleShot(3500, self._refresh)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _disable(self):
        if QMessageBox.question(self, "Disable Band Lock",
            "Disable Band Lock and revert to automatic band selection?",
            QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            rapi.set_band_lock(self.client, False, lte_bands=[], nr_bands=[])
            QMessageBox.information(self, "Disabled",
                "Band Lock disabled. All bands available again.")
            QTimer.singleShot(3500, self._refresh)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
