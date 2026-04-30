"""Preflight dialog — first-run system check.

Shown before the LoginDialog when no recent pass-flag exists. Each check
appears as a row with an icon, label, and detail. If VC++ is missing, an
"Install" button downloads + silently runs Microsoft's redist.

The whole flow is GUI-only: the actual checks live in preflight.py.
"""
from PyQt5.QtCore    import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QProgressBar)

from shared import preflight, debug_log


# ───── Background workers ─────
class _ChecksWorker(QThread):
    """Run all_checks() off the GUI thread so the dialog stays responsive."""
    result = pyqtSignal(list)
    def run(self):
        try:
            self.result.emit(preflight.all_checks())
        except Exception as e:
            debug_log.exc(f"preflight checks worker failed: {e}", "preflight")
            self.result.emit([])


class _VCInstallWorker(QThread):
    progress = pyqtSignal(str)
    done     = pyqtSignal(bool, str)
    def run(self):
        try:
            self.progress.emit("Downloading installer from Microsoft…")
            ok, msg = preflight.install_vcredist()
            self.done.emit(ok, msg)
        except Exception as e:
            debug_log.exc(f"VC install worker failed: {e}", "preflight")
            self.done.emit(False, str(e))


# ───── Main dialog ─────
_CHECK_ROWS = [
    ("vcredist", "Visual C++ Runtime",
                  "Required by Qt — typically pre-installed on Win 10/11"),
    ("router",   "Router Connectivity",
                  "Direct LAN connection to 192.168.8.1"),
    ("internet", "Internet Access",
                  "For IP Scan + Speed Test (Fast.com)"),
    ("config",   "Config Directory",
                  "Saved login + theme preferences"),
]


class PreflightDialog(QDialog):
    """Modal: blocks app startup until the user acknowledges OR every
    check passes. Returns Accepted on continue, Rejected on close."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FiberHome Manager — System Check")
        self.setModal(True)
        self.setFixedWidth(560)
        self._checks_worker = None
        self._inst_worker   = None
        self._build_ui()
        # Run the first pass automatically — no point making the user click.
        self._run_checks()

    # ── UI ──
    def _build_ui(self):
        v = QVBoxLayout(self); v.setContentsMargins(28, 24, 28, 22); v.setSpacing(12)

        title = QLabel("⚙  System Check")
        title.setStyleSheet("color:#0D47A1; font-size:24px; font-weight:bold;")
        title.setAlignment(Qt.AlignCenter)
        v.addWidget(title)

        sub = QLabel("Verifying everything we need is in place before launch")
        sub.setStyleSheet("color:#78909C; font-size:11px;")
        sub.setAlignment(Qt.AlignCenter)
        v.addWidget(sub)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background:#E0E4E8;")
        v.addWidget(sep)

        # Per-check rows ----------
        self._rows = {}   # key -> (chip, label, detail)
        for key, label, sub_text in _CHECK_ROWS:
            row = QHBoxLayout(); row.setSpacing(10)
            chip = QLabel("⏳"); chip.setMinimumWidth(28)
            chip.setStyleSheet("font-size:18px;")
            row.addWidget(chip)
            box = QVBoxLayout(); box.setSpacing(0)
            l_main = QLabel(label)
            l_main.setStyleSheet("color:#37474F; font-size:13px; font-weight:bold;")
            l_sub  = QLabel(sub_text)
            l_sub.setStyleSheet("color:#90A4AE; font-size:10px;")
            box.addWidget(l_main); box.addWidget(l_sub)
            row.addLayout(box, 1)
            detail = QLabel("checking…")
            detail.setStyleSheet("color:#78909C; font-size:11px;")
            detail.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(detail)
            v.addLayout(row)
            self._rows[key] = (chip, l_main, detail)

        # Status / progress line ----------
        self._lbl_status = QLabel(" ")
        self._lbl_status.setStyleSheet("color:#37474F; font-size:11px;")
        self._lbl_status.setAlignment(Qt.AlignCenter)
        v.addWidget(self._lbl_status)

        # Action buttons ----------
        btn_row = QHBoxLayout()
        self._btn_install = QPushButton("⬇  Install Visual C++ Runtime")
        self._btn_install.setVisible(False)
        self._btn_install.setStyleSheet(
            "QPushButton { background:#0D47A1; color:#FFFFFF; border:none; "
             "border-radius:5px; padding:8px 18px; font-weight:bold; font-size:12px; }"
            "QPushButton:hover { background:#1565C0; }"
            "QPushButton:disabled { background:#90A4AE; }")
        self._btn_install.clicked.connect(self._on_install)
        btn_row.addWidget(self._btn_install)

        self._btn_recheck = QPushButton("⟳  Re-check")
        self._btn_recheck.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#0D47A1; "
             "border:1px solid #0D47A1; border-radius:5px; "
             "padding:8px 18px; font-weight:bold; font-size:12px; }"
            "QPushButton:hover { background:#E3F2FD; }")
        self._btn_recheck.clicked.connect(self._run_checks)
        btn_row.addWidget(self._btn_recheck)

        btn_row.addStretch()

        self._btn_continue = QPushButton("Continue  →")
        self._btn_continue.setEnabled(False)
        self._btn_continue.setMinimumWidth(140)
        self._btn_continue.setStyleSheet(
            "QPushButton { background:#10B981; color:#FFFFFF; border:none; "
             "border-radius:5px; padding:8px 24px; font-weight:bold; font-size:12px; }"
            "QPushButton:disabled { background:#B0BEC5; color:#FFFFFF; }"
            "QPushButton:hover:enabled { background:#059669; }")
        self._btn_continue.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_continue)
        v.addLayout(btn_row)

    # ── Run checks ──
    def _run_checks(self):
        for chip, _, det in self._rows.values():
            chip.setText("⏳")
            det.setText("checking…")
            det.setStyleSheet("color:#78909C; font-size:11px;")
        self._btn_continue.setEnabled(False)
        self._btn_install.setVisible(False)
        self._lbl_status.setText("Running checks…")
        self._lbl_status.setStyleSheet("color:#78909C; font-size:11px;")

        debug_log.info("preflight: running checks", "preflight")
        self._checks_worker = _ChecksWorker()
        self._checks_worker.result.connect(self._on_results)
        self._checks_worker.start()

    def _on_results(self, results):
        if not results:
            self._lbl_status.setText("Check runner failed — see log file.")
            self._lbl_status.setStyleSheet(
                "color:#EF4444; font-size:12px; font-weight:bold;")
            return
        all_ok = True
        vc_missing = False
        for key, ok, detail in results:
            if key not in self._rows: continue
            chip, _, det = self._rows[key]
            if ok:
                chip.setText("✅")
                det.setText(detail)
                det.setStyleSheet("color:#10B981; font-size:11px;")
            else:
                chip.setText("❌")
                det.setText(detail)
                det.setStyleSheet("color:#EF4444; font-size:11px;")
                all_ok = False
                if key == "vcredist": vc_missing = True
            debug_log.info(f"preflight {key}: {'PASS' if ok else 'FAIL'} — {detail}",
                            "preflight")

        if all_ok:
            self._lbl_status.setText("✓  All checks passed — you're good to go.")
            self._lbl_status.setStyleSheet(
                "color:#10B981; font-size:12px; font-weight:bold;")
            self._btn_continue.setEnabled(True)
            preflight.mark_passed()
        else:
            self._lbl_status.setText(
                "Fix the issues above, then re-check.")
            self._lbl_status.setStyleSheet(
                "color:#EF4444; font-size:12px; font-weight:bold;")
            if vc_missing:
                self._btn_install.setVisible(True)

    # ── VC++ install ──
    def _on_install(self):
        self._btn_install.setEnabled(False)
        self._btn_install.setText("Installing… (this may take a minute)")
        self._lbl_status.setText("Downloading from Microsoft…")
        self._lbl_status.setStyleSheet("color:#0D47A1; font-size:11px;")
        debug_log.info("preflight: installing VC++ Redistributable", "preflight")

        self._inst_worker = _VCInstallWorker()
        self._inst_worker.progress.connect(self._on_install_progress)
        self._inst_worker.done.connect(self._on_install_done)
        self._inst_worker.start()

    def _on_install_progress(self, msg):
        self._lbl_status.setText(msg)

    def _on_install_done(self, ok, msg):
        self._btn_install.setEnabled(True)
        self._btn_install.setText("⬇  Install Visual C++ Runtime")
        if ok:
            debug_log.info(f"preflight: VC++ install succeeded ({msg})",
                            "preflight")
            self._lbl_status.setText("Installed — re-checking…")
            self._run_checks()
        else:
            debug_log.error(f"preflight: VC++ install failed ({msg})",
                             "preflight")
            self._lbl_status.setText(f"Install failed: {msg}")
            self._lbl_status.setStyleSheet(
                "color:#EF4444; font-size:11px; font-weight:bold;")
