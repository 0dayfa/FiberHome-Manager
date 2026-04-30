"""Design 1 — Engineering Console (HMPy-style dense single page)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "shared")))

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QGridLayout, QLabel, QFrame, QPushButton, QLineEdit,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QAbstractItemView, QStackedWidget, QButtonGroup,
                              QMessageBox, QComboBox, QCheckBox, QSpinBox,
                              QScrollArea)
from PyQt5.QtCore    import Qt, QTimer, QSize, QByteArray
from PyQt5.QtGui     import QColor, QFont, QPixmap, QFontDatabase
from PyQt5.QtSvg     import QSvgWidget
from shared.data_hub import run_design
from shared import auth_store, themes as theme_mod, i18n, debug_log

import router_api as rapi


def _logo_path(name="logo_icon.svg"):
    """Resolve a bundled SVG asset at runtime — works whether the app
    runs from source (project tree) or as a PyInstaller frozen one-folder."""
    import os, sys
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "shared", "assets", name),
        os.path.join(getattr(sys, "_MEIPASS", ""), "shared", "assets", name),
        os.path.join(os.path.dirname(sys.argv[0]), "shared", "assets", name),
        os.path.join(os.path.dirname(sys.argv[0]), "_internal", "shared", "assets", name),
    ]
    for p in candidates:
        if p and os.path.isfile(p): return p
    return None


def _themed_logo_bytes():
    """Read the full routers.world wordmark SVG and recolor its dark grey
    text gradient (#606060 → #1f1f1f) so the lettering reads on the
    active theme. The cyan signal-arc accent (#79a2ed) is left alone."""
    p = _logo_path("logo.svg")
    if not p: return None
    try:
        with open(p, "rb") as f:
            svg = f.read().decode("utf-8")
    except Exception:
        return None
    if theme_mod.current() != "light":
        # Wordmark gradient stops are dark grey — invisible on dark canvases.
        svg = svg.replace('stop-color="#606060"', f'stop-color="{theme_mod.t("fg")}"')
        svg = svg.replace('stop-color="#1f1f1f"', f'stop-color="{theme_mod.t("fg_dim")}"')
    return QByteArray(svg.encode("utf-8"))
from widgets.live_chart import LiveChart
from designs.d01_engineering.usage_gauge import UsageGauge
from designs.d01_engineering.zone_chart import (ZoneChart,
                                                 RSRP_ZONES, RSRQ_ZONES,
                                                 SINR_ZONES, RSSI_ZONES)


STYLE = """
QWidget { background: #F5F5F5; color: #222; font-family: 'Segoe UI'; font-size: 12px; }
QMainWindow { background: #E8E8E8; }
QLabel#section { color:#666; font-size:11px; font-weight:bold; }
QLabel#hdrtext { color:#333; font-weight:bold; font-size:12px; }
QLineEdit { background: #FFFFFF; border: 1px solid #B0B0B0; border-radius:2px;
             padding: 3px 6px; color: #222; font-family: 'Consolas'; font-size: 12px; }
QLineEdit:read-only { background:#FFFFFF; }
QPushButton { background:#FFFFFF; border:1px solid #888; border-radius:2px; padding:5px 10px;
              color:#222; font-size:12px; }
QPushButton:hover { background:#E0E0E0; }
QPushButton#topbtn { padding: 6px 16px; background:#FCFCFC; border:1px solid #999;
                     font-weight:bold; }
QPushButton#topbtn:checked { background:#0D47A1; color:#FFFFFF; border-color:#0D47A1; }
QPushButton#topbtn:hover { background:#E0E0E0; }
QPushButton#topbtn:checked:hover { background:#1565C0; }
QFrame#group { background:#FFFFFF; border:1px solid #D0D0D0; border-radius:2px; }
QLabel.green { background:#90EE90; padding:3px 6px; border:1px solid #5C9; }
QLabel.yellow { background:#FFEB99; padding:3px 6px; border:1px solid #C0A030; }
QLabel.blue   { background:#7FBFFF; padding:3px 6px; border:1px solid #4080C0; color:white; }
QLabel.red    { background:#FF8080; padding:3px 6px; border:1px solid #B04040; color:white; }
QLabel.gray   { background:#D8D8D8; padding:3px 6px; border:1px solid #888; }
"""


def _ro(text=""):
    e = QLineEdit(text); e.setReadOnly(True); return e


def _group(title="", parent=None):
    f = QFrame(parent); f.setObjectName("group")
    return f


class EngWindow(QMainWindow):
    def __init__(self, hub):
        super().__init__()
        debug_log.info("main window constructed", "ui")
        self.hub = hub
        self.setWindowTitle(i18n.s("AppName"))
        # App-wide theme is applied at run_design boot; honor it here too
        self.setStyleSheet(theme_mod.app_qss())
        self._size_to_screen()
        # Tracked async workers — kept alive on the instance so they aren't
        # garbage-collected mid-flight, and so we can stop them on rebuild.
        self._async_workers = []
        self._build()
        self.hub.updated.connect(self._on_data)
        self.hub.auth_status.connect(self._on_auth)

    # ── Responsive layout ──
    def resizeEvent(self, ev):
        """Override to drive 'media-query'-style breakpoints. Modern apps
        do this via JS/CSS — Qt has no built-in equivalent, so we do it
        manually on every resize tick."""
        super().resizeEvent(ev)
        try: self._apply_responsive_layout()
        except Exception: pass

    def _apply_responsive_layout(self):
        """Hide / show secondary panels based on current window size and
        the user's Charts preference. Runs on every resize tick — kept
        cheap (just .setVisible() calls)."""
        if not hasattr(self, "_charts_row"): return
        w, h = self.width(), self.height()
        # Charts auto-hide rules:
        #   user toggle off            → hide
        #   width  < 1100 (narrow)     → hide (per Q1 plan)
        #   height < 700  (short)      → hide
        user_pref = bool(getattr(self, "_charts_toggle", None)
                         and self._charts_toggle.isChecked())
        fits = (w >= 1100 and h >= 700)
        self._charts_row.setVisible(user_pref and fits)

    def _on_charts_toggle(self, checked):
        auth_store.set_pref("show_charts", bool(checked))
        debug_log.info(f"charts toggle → {checked}", "ui")
        self._apply_responsive_layout()

    def _async_call(self, fn, on_done):
        """Run a blocking router call OFF the GUI thread.
        `fn`     : zero-arg callable that returns the result (any type).
        `on_done`: receives whatever fn returned, or {'__error__': str}.
        Without this every Apply / Refresh button froze the window for
        2-15 seconds on slow LANs (VMs, low-RSRP cellular)."""
        from PyQt5.QtCore import QThread, pyqtSignal as _Sig
        class _W(QThread):
            result = _Sig(object)
            def run(self):
                try:    self.result.emit(fn())
                except Exception as e:
                    debug_log.exc(f"async call failed: {e}", "async")
                    self.result.emit({"__error__": str(e)})
        w = _W()
        w.result.connect(on_done)
        # Self-cleanup: drop the reference once the thread finishes so the
        # list doesn't grow unbounded across a long session.
        w.finished.connect(lambda w=w: self._async_workers.remove(w)
                              if w in self._async_workers else None)
        self._async_workers.append(w)
        w.start()
        return w

    def _size_to_screen(self):
        """Size + place the window relative to the active monitor.
        Tighter min size (980×640) so it fits comfortably on 720p
        laptops without overflowing."""
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1280, 800); return
        avail = screen.availableGeometry()   # excludes taskbar
        target_w = max(1100, min(int(avail.width()  * 0.88), 1920))
        target_h = max(720,  min(int(avail.height() * 0.88), 1200))
        # Looser floor — chips & charts have responsive paint so they
        # render fine all the way down to 980×640.
        self.setMinimumSize(980, 640)
        self.resize(target_w, target_h)
        # Centre on the screen so the window never spawns off-edge on
        # multi-monitor setups.
        self.move(avail.center().x() - target_w // 2,
                   avail.center().y() - target_h // 2)
        debug_log.info(
            f"window sized {target_w}x{target_h} on screen "
            f"{avail.width()}x{avail.height()}", "ui")

    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(8, 8, 8, 8); root.setSpacing(8)

        # ── Top bar (acts as tab switcher) ──
        top = QHBoxLayout(); top.setSpacing(6)
        self._top_btns = {}
        self._top_group = QButtonGroup(self); self._top_group.setExclusive(True)

        # Tab buttons (translated)
        tab_keys = ["Main","Band Select","Advance","Settings","IP Scan","AT Command"]
        for key in tab_keys:
            b = QPushButton(i18n.s(key)); b.setObjectName("topbtn")
            b.setCheckable(True)
            self._top_btns[key] = b
            top.addWidget(b)
            self._top_group.addButton(b)
        self._top_btns["Main"].setChecked(True)
        self._top_btns["Main"].clicked.connect(lambda: self._show_view("main"))
        self._top_btns["Band Select"].clicked.connect(lambda: self._show_view("band"))
        self._top_btns["Advance"].clicked.connect(lambda: self._show_view("advance"))
        self._top_btns["Settings"].clicked.connect(lambda: self._show_view("settings"))
        self._top_btns["IP Scan"].clicked.connect(lambda: self._show_view("ipscan"))
        self._top_btns["AT Command"].clicked.connect(lambda: self._show_view("atcmd"))

        top.addStretch()

        # Charts toggle — auto-hides when window is short, but the user
        # can also force it via this checkbox. Preference persists across
        # sessions in the .fiberguard/config.json bag.
        self._charts_toggle = QPushButton("📊 Charts")
        self._charts_toggle.setObjectName("topbtn")
        self._charts_toggle.setCheckable(True)
        self._charts_toggle.setChecked(
            bool(auth_store.get_pref("show_charts", True)))
        self._charts_toggle.toggled.connect(self._on_charts_toggle)
        top.addWidget(self._charts_toggle)

        # Language switcher
        self._lang_box = QComboBox(); self._lang_box.setMinimumWidth(110)
        for code, lbl in [("en", "🌐 English"), ("ar", "🌐 العربيه")]:
            self._lang_box.addItem(lbl, code)
        idx = self._lang_box.findData(i18n.current())
        if idx >= 0: self._lang_box.setCurrentIndex(idx)
        self._lang_box.currentIndexChanged.connect(self._on_lang_change)
        top.addWidget(self._lang_box)

        # Theme switcher (live)
        self._theme_box = QComboBox(); self._theme_box.setMinimumWidth(120)
        for code, lbl in [("light","☼ Light"),("dark","◐ Dark"),("aurora","✦ Aurora")]:
            self._theme_box.addItem(lbl, code)
        cur = theme_mod.current()
        idx = self._theme_box.findData(cur)
        if idx >= 0: self._theme_box.setCurrentIndex(idx)
        self._theme_box.currentIndexChanged.connect(self._on_theme_change)
        top.addWidget(self._theme_box)

        # User chip
        u, _, _ = auth_store.load_credentials()
        self._user_chip = QLabel(f"👤  {u or self.hub.user}")
        self._user_chip.setStyleSheet(
            f"color:{theme_mod.t('accent')}; font-size:12px; font-weight:bold; "
            f"padding:6px 12px; background:{theme_mod.t('accent_bg')}; "
            f"border:1px solid {theme_mod.t('accent')}; border-radius:14px;")
        top.addWidget(self._user_chip)

        # Restart router + Logout
        rb = QPushButton(i18n.s("Restart Router")); rb.setObjectName("topbtn")
        rb.clicked.connect(self._on_restart_router)
        top.addWidget(rb)

        logout = QPushButton("⏻  " + i18n.s("Logout")); logout.setObjectName("topbtn")
        logout.clicked.connect(self._on_logout)
        top.addWidget(logout)

        root.addLayout(top)

        # ── Stack: page_main + page_band ──
        self.view_stack = QStackedWidget()
        root.addWidget(self.view_stack, 1)

        # Build main page — fluid layout, no scroll. Bottom charts auto-
        # hide when the window can't fit them (handled by resizeEvent).
        self.page_main = QWidget()
        page_main_lay = QVBoxLayout(self.page_main)
        page_main_lay.setContentsMargins(8, 8, 8, 8); page_main_lay.setSpacing(8)
        self.view_stack.addWidget(self.page_main)

        # Build band-select page
        self.page_band = self._build_band_page()
        self.view_stack.addWidget(self.page_band)

        # Build advance page
        self.page_advance = self._build_advance_page()
        self.view_stack.addWidget(self.page_advance)

        # Build settings page (placeholder for now — built next)
        self.page_settings = self._build_settings_page() \
            if hasattr(self, "_build_settings_page") else QWidget()
        self.view_stack.addWidget(self.page_settings)

        # Build IP Scan page
        self.page_ipscan = self._build_ipscan_page() \
            if hasattr(self, "_build_ipscan_page") else QWidget()
        self.view_stack.addWidget(self.page_ipscan)

        # Build AT Command page
        self.page_atcmd = self._build_atcmd_page() \
            if hasattr(self, "_build_atcmd_page") else QWidget()
        self.view_stack.addWidget(self.page_atcmd)

        # Insert main content into page_main (the existing top_row + charts)
        # ════════════════════════════════════════════════════════════════
        # MAIN PAGE — horizontal-first layout (v2)
        # Replaces the v1 vertical-stacked design. Goal: every panel uses
        # its width budget. v1 backup at _archive/old_designs/d01_main_v1_vertical.py
        # ════════════════════════════════════════════════════════════════

        # ── ROW A: System Monitors | General Info chips | Network Info ──
        row_a = QHBoxLayout(); row_a.setSpacing(8)

        # LEFT panel: 3 gauges (compact horizontal)
        lt_g = _group()
        lt_l = QVBoxLayout(lt_g); lt_l.setContentsMargins(8, 6, 8, 6); lt_l.setSpacing(4)

        t = theme_mod.t

        # ── 3 gauges horizontally inside the System Monitors panel ──
        lt_l.addWidget(self._title("System Monitors"))
        gauges_row = QHBoxLayout(); gauges_row.setSpacing(4)
        self.gauge_temp = UsageGauge(
            "MODEM", "°C", 0, 100,
            thresholds=[(50, "#10B981"), (70, "#FACC15"),
                         (85, "#F59E0B"), (101, "#EF4444")])
        self.gauge_cpu = UsageGauge("CPU", "%", 0, 100)
        self.gauge_ram = UsageGauge("RAM", "%", 0, 100)
        for g in (self.gauge_temp, self.gauge_cpu, self.gauge_ram):
            g.setMinimumSize(96, 96)
            gauges_row.addWidget(g, 1)
        lt_l.addLayout(gauges_row, 1)
        row_a.addWidget(lt_g, 0)            # gauges fixed-ish width

        # ── General Info: HORIZONTAL chip strip ──
        # Each chip is "label · value" stacked tightly. Six chips share the
        # available width via stretch — no fixed minWidth, so they shrink
        # gracefully on narrow windows.
        gi_panel = _group()
        gi_lay = QVBoxLayout(gi_panel); gi_lay.setContentsMargins(8, 6, 8, 6); gi_lay.setSpacing(4)
        gi_lay.addWidget(self._title("General Info"))
        gi_row = QHBoxLayout(); gi_row.setSpacing(6)
        self._conn = {}
        cnames = [("Connection",      "connstat"),
                  ("Signal (4G+5G)",  "signal"),
                  ("5G Status",       "status5g"),
                  ("Network Type",    "nettype"),
                  ("Mode · 5G Opt",   "nettypeex"),
                  ("Software Ver",    "swver")]
        for lbl, fid in cnames:
            cell = QVBoxLayout(); cell.setSpacing(2); cell.setContentsMargins(0, 0, 0, 0)
            cap = QLabel(i18n.s(lbl))
            cap.setStyleSheet(
                f"color:{t('fg_dim')}; font-size:9px; font-weight:bold; "
                f"letter-spacing:1px; background:transparent;")
            cap.setAlignment(Qt.AlignCenter)
            chip = QLabel("—"); chip.setObjectName(fid)
            chip.setStyleSheet(
                f"background:{t('card_alt')}; color:{t('fg')}; padding:5px 8px; "
                f"border:1px solid {t('border')}; border-radius:4px; "
                f"font-size:11px; font-weight:600;")
            chip.setAlignment(Qt.AlignCenter)
            self._conn[fid] = chip
            cell.addWidget(cap); cell.addWidget(chip)
            gi_row.addLayout(cell, 1)
        gi_lay.addLayout(gi_row)
        row_a.addWidget(gi_panel, 5)        # main width consumer in row A

        # ── Network Info compact (PLMN + SPN + run-time) ──
        ni_panel = _group()
        ni_lay = QVBoxLayout(ni_panel); ni_lay.setContentsMargins(8, 6, 8, 6); ni_lay.setSpacing(3)
        ni_lay.addWidget(self._title("Network Info"))
        self._net = {}
        for fid, label_text in [("plmn", "PLMN"), ("spn", "SPN")]:
            r = QHBoxLayout(); r.setSpacing(6); r.setContentsMargins(0, 0, 0, 0)
            cap = QLabel(label_text)
            cap.setStyleSheet(
                f"color:{t('fg_dim')}; font-size:10px; font-weight:bold; "
                f"letter-spacing:1px; background:transparent;")
            cap.setFixedWidth(38)
            v = _ro(); self._net[fid] = v
            r.addWidget(cap); r.addWidget(v, 1)
            ni_lay.addLayout(r)
        # App run-time mini-row
        rt_row = QHBoxLayout()
        rt_lbl = QLabel(i18n.s("Total App Run Time"))
        rt_lbl.setStyleSheet(f"color:{t('fg_dim')}; font-size:10px; "
                              f"font-weight:bold; background:transparent;")
        self._app_time = QLabel("00:00:00")
        self._app_time.setStyleSheet(f"font-family:Consolas; font-size:12px; "
                                       f"font-weight:bold; color:{t('accent')};")
        rt_row.addWidget(rt_lbl); rt_row.addWidget(self._app_time); rt_row.addStretch()
        ni_lay.addLayout(rt_row)
        ni_lay.addStretch()
        row_a.addWidget(ni_panel, 2)

        page_main_lay.addLayout(row_a, 0)

        # ── ROW B: Traffic Statistics (single horizontal row) ──
        traf_panel = _group()
        traf_lay = QVBoxLayout(traf_panel); traf_lay.setContentsMargins(8, 4, 8, 4); traf_lay.setSpacing(2)
        traf_lay.addWidget(self._title("Traffic Statistics"))
        traf_row = QHBoxLayout(); traf_row.setSpacing(8)
        self._traf = {}
        # Up/Dn rates were dropped — they flickered between "0.0 KB" and
        # "—" because the rate calc needs two consecutive non-empty
        # snapshots, and the firmware sometimes returns blanks. The Total
        # counters below are stable and convey the same info.
        tnames = [("Σ↑ Today",      "up_now"),
                   ("Σ↓ Today",      "dn_now"),
                   ("Σ↑ Total",      "up_total"),
                   ("Σ↓ Total",      "dn_total"),
                   ("Conn (Total)",  "conn_total"),
                   ("Conn (Now)",    "conn_now")]
        for lbl, fid in tnames:
            cell = QVBoxLayout(); cell.setSpacing(1); cell.setContentsMargins(0, 0, 0, 0)
            cap = QLabel(lbl)
            cap.setStyleSheet(
                f"color:{t('fg_dim')}; font-size:9px; font-weight:bold; "
                f"letter-spacing:0.5px; background:transparent;")
            cap.setAlignment(Qt.AlignCenter)
            v = QLineEdit(); v.setReadOnly(True); v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(
                f"background:{t('card_alt')}; color:{t('fg')}; padding:3px 6px; "
                f"border:1px solid {t('border')}; border-radius:3px; "
                f"font-family:Consolas; font-size:11px; font-weight:bold;")
            self._traf[fid] = v
            cell.addWidget(cap); cell.addWidget(v)
            traf_row.addLayout(cell, 1)
        traf_lay.addLayout(traf_row)
        page_main_lay.addWidget(traf_panel, 0)

        # ── ROW C: Carrier Aggregation table — wide, full row ──
        ca_panel = _group()
        ca_lay = QVBoxLayout(ca_panel); ca_lay.setContentsMargins(8, 4, 8, 4); ca_lay.setSpacing(2)
        ca_lay.addWidget(self._title("Carrier Aggregation"))
        self.ca_table = QTableWidget(0, 6)
        self.ca_table.setHorizontalHeaderLabels(
            ["Parameters", "PCC", "PCC", "SCC-1", "SCC-2", "SCC-3"])
        h = self.ca_table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setDefaultAlignment(Qt.AlignCenter)
        self.ca_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ca_table.setAlternatingRowColors(True)
        self.ca_table.verticalHeader().setVisible(False)
        self.ca_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.ca_table.verticalHeader().setDefaultSectionSize(24)
        self.ca_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ca_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ca_table.setStyleSheet(
            f"QTableWidget {{ background:{t('card')}; color:{t('fg')}; "
            f"gridline-color:{t('border_lt')}; "
            f"alternate-background-color:{t('card_alt')}; font-size:11px; "
            f"selection-background-color:{t('accent_bg')}; selection-color:{t('fg')}; }}"
            f"QTableWidget::item {{ padding:2px 6px; }}"
            f"QHeaderView::section {{ background:{t('card_alt')}; color:{t('fg')}; "
            f"border:1px solid {t('border')}; padding:4px; font-weight:bold; font-size:11px; }}")
        params = ["Type","State","Band","PCI","Arfcn","DL_BandWidth"]
        self.ca_table.setRowCount(len(params))
        for i, p in enumerate(params):
            it = QTableWidgetItem(p)
            it.setTextAlignment(Qt.AlignCenter)
            f = QFont("Segoe UI", 9, QFont.Bold); it.setFont(f)
            it.setForeground(QColor(t("fg_dim")))
            self.ca_table.setItem(i, 0, it)
            for c in range(1, 6):
                self.ca_table.setItem(i, c, QTableWidgetItem("—"))
        self._ca_params = params
        self.ca_table.setMaximumHeight(24 * (len(params) + 1) + 8)
        ca_lay.addWidget(self.ca_table)
        page_main_lay.addWidget(ca_panel, 0)

        # ── ROW D: 5G NR + 4G LTE chips, side by side, HORIZONTAL fields ──
        rf_row = QHBoxLayout(); rf_row.setSpacing(8)
        nr_fields = [("BAND","band"),("PCI","pci"),("RSRP","rsrp"),
                      ("RSRQ","rsrq"),("SINR","sinr"),("RSSI","rssi"),
                      ("Power","power"),("CQI","cqi"),("QCI","qci"),
                      ("CELL","cellid")]

        def _build_rf_panel_h(title, accent, store_attr):
            """RF strip rendered as a 1-row QTableWidget — matches the CA
            table's visual language (same gridlines, same header style)
            so the page reads as a coherent dashboard, not random chips."""
            box = _group()
            v = QVBoxLayout(box); v.setContentsMargins(8, 4, 8, 4); v.setSpacing(2)
            head = QLabel(title)
            head.setStyleSheet(f"color:{accent}; font-size:11px; font-weight:bold; "
                                f"letter-spacing:2px; padding:2px 4px;")
            v.addWidget(head)

            table = QTableWidget(1, len(nr_fields))
            table.setHorizontalHeaderLabels([lbl for lbl, _ in nr_fields])
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.NoSelection)
            table.setFocusPolicy(Qt.NoFocus)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table.setStyleSheet(
                f"QTableWidget {{ background:{t('card')}; color:{t('fg')}; "
                f"gridline-color:{t('border_lt')}; font-size:11px; "
                f"selection-background-color:{t('card_alt')}; }}"
                f"QTableWidget::item {{ padding:4px 6px; }}"
                f"QHeaderView::section {{ background:{t('card_alt')}; "
                f"color:{t('fg_dim')}; border:1px solid {t('border_lt')}; "
                f"padding:3px; font-weight:bold; font-size:9px; "
                f"letter-spacing:0.5px; }}")
            table.setRowHeight(0, 30)
            # Header (~26px) + value row (30px) + 2px borders
            table.setMaximumHeight(60)
            table.setMinimumHeight(60)

            store = {}
            for col, (_, fid) in enumerate(nr_fields):
                item = QTableWidgetItem("—")
                item.setTextAlignment(Qt.AlignCenter)
                f = QFont("Consolas", 10); f.setBold(True)
                item.setFont(f)
                table.setItem(0, col, item)
                store[fid] = item
            setattr(self, store_attr, store)
            v.addWidget(table)
            return box

        nr_box  = _build_rf_panel_h("5G NR",  t("accent"), "_nr")
        lte_box = _build_rf_panel_h("4G LTE", t("ok") if theme_mod.current() == "light"
                                      else t("accent_2"), "_lte")
        rf_row.addWidget(nr_box, 1)
        rf_row.addWidget(lte_box, 1)
        page_main_lay.addLayout(rf_row, 0)

        # ── ROW E: Charts (smaller — 4G | 5G) ──
        ch = _group()
        chl = QHBoxLayout(ch); chl.setContentsMargins(6, 4, 6, 6); chl.setSpacing(6)

        col4g = QFrame(); col4g.setObjectName("group")
        c4 = QVBoxLayout(col4g); c4.setContentsMargins(6, 4, 6, 6); c4.setSpacing(4)
        h4 = QLabel("4G LTE")
        h4.setStyleSheet(f"color:{t('ok')}; font-size:11px; font-weight:bold; "
                          "letter-spacing:3px; padding:1px 2px;")
        c4.addWidget(h4)
        self.zc_4g_rsrp = ZoneChart("RSRP", " dBm", RSRP_ZONES, "#10B981")
        self.zc_4g_rssi = ZoneChart("RSSI", " dBm", RSSI_ZONES, "#22C55E")
        self.zc_4g_rsrq = ZoneChart("RSRQ", " dB",  RSRQ_ZONES, "#A78BFA")
        self.zc_4g_sinr = ZoneChart("SINR", " dB",  SINR_ZONES, "#F59E0B")
        for z in (self.zc_4g_rsrp, self.zc_4g_rssi, self.zc_4g_rsrq, self.zc_4g_sinr):
            z.setMinimumHeight(60)        # smaller — was 95
            c4.addWidget(z, 1)
        chl.addWidget(col4g, 1)

        col5g = QFrame(); col5g.setObjectName("group")
        c5 = QVBoxLayout(col5g); c5.setContentsMargins(6, 4, 6, 6); c5.setSpacing(4)
        h5 = QLabel("5G NR")
        h5.setStyleSheet(f"color:{t('accent')}; font-size:11px; font-weight:bold; "
                          "letter-spacing:3px; padding:1px 2px;")
        c5.addWidget(h5)
        self.zc_5g_rsrp = ZoneChart("RSRP", " dBm", RSRP_ZONES, "#3B82F6")
        self.zc_5g_rssi = ZoneChart("RSSI", " dBm", RSSI_ZONES, "#06B6D4")
        self.zc_5g_rsrq = ZoneChart("RSRQ", " dB",  RSRQ_ZONES, "#EC4899")
        self.zc_5g_sinr = ZoneChart("SINR", " dB",  SINR_ZONES, "#FBBF24")
        for z in (self.zc_5g_rsrp, self.zc_5g_rssi, self.zc_5g_rsrq, self.zc_5g_sinr):
            z.setMinimumHeight(60)
            c5.addWidget(z, 1)
        chl.addWidget(col5g, 1)

        # Track for the responsive auto-hide rule (Q1 plan).
        self._charts_row = ch
        page_main_lay.addWidget(ch, 1)      # stretch 1: takes leftover height

        # ── Bottom bar: centred brand (credit · routers.world) + status ──
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(10, 4, 10, 4); brand_row.setSpacing(0)

        # Left padding so the centred block sits visually in the middle
        brand_row.addStretch(1)

        # "Made by: Fahad" — upright, bold, no italic
        self._brand_credit = QLabel(i18n.s("MadeBy"))
        credit_font = QFont("Cambria", 14); credit_font.setBold(True)
        self._brand_credit.setFont(credit_font)
        self._brand_credit.setStyleSheet(
            f"color:{theme_mod.t('fg')}; letter-spacing:1px; "
            "background:transparent;")
        brand_row.addWidget(self._brand_credit, 0, Qt.AlignVCenter)

        # Separator dot
        sep = QLabel("  ·  ")
        sep.setStyleSheet(f"color:{theme_mod.t('fg_mute')}; font-size:14px; "
                           "background:transparent;")
        brand_row.addWidget(sep, 0, Qt.AlignVCenter)

        # routers.world — slightly larger, accent-colored, clickable visual
        self._brand_world = QLabel("routers.world")
        world_font = QFont("Cambria", 16); world_font.setBold(True)
        self._brand_world.setFont(world_font)
        self._brand_world.setStyleSheet(
            f"color:{theme_mod.t('accent')}; letter-spacing:1.5px; "
            "background:transparent;")
        brand_row.addWidget(self._brand_world, 0, Qt.AlignVCenter)

        brand_row.addStretch(1)

        # Connection status anchored to the right edge.
        self.status_lbl = QLabel(f"● {i18n.s('Connecting...')}")
        self.status_lbl.setStyleSheet(f"color:{theme_mod.t('warn')}; "
                                        "font-weight:bold; font-size:11px; "
                                        "background:transparent;")
        brand_row.addWidget(self.status_lbl, 0, Qt.AlignVCenter)
        root.addLayout(brand_row)

        # uptime updater
        from PyQt5.QtCore import QTimer
        self._t0 = None
        self._tick_t = QTimer(self); self._tick_t.timeout.connect(self._tick); self._tick_t.start(1000)

    def _title(self, txt):
        # Translate the title key transparently — callers can pass either
        # an English label or an i18n key, the lookup falls through if absent.
        translated = i18n.s(txt)
        l = QLabel(translated.upper()); l.setObjectName("section")
        l.setStyleSheet(f"color:{theme_mod.t('fg_dim')}; font-size:15px; "
                         "font-weight:bold; letter-spacing:2px;")
        l.setAlignment(Qt.AlignCenter)
        return l

    def _tick(self):
        import time
        if self._t0 is None: return
        sec = int(time.time() - self._t0)
        h, m, s = sec // 3600, (sec // 60) % 60, sec % 60
        self._app_time.setText(f"{h:01d}:{m:02d}:{s:02d}")

    def _set_chip(self, w, val, color=None):
        """Set value + optional background color on either a QLabel chip
        OR a QTableWidgetItem (the v2 RF strips use the latter)."""
        text = str(val) if val not in (None, "") else "—"
        t = theme_mod.t
        fg = "#FFFFFF" if theme_mod.current() != "light" else t("fg")
        if isinstance(w, QTableWidgetItem):
            w.setText(text)
            if color:
                from PyQt5.QtGui import QBrush
                w.setBackground(QBrush(QColor(color)))
                w.setForeground(QBrush(QColor(fg)))
            else:
                # Reset to defaults so a previously-coloured cell goes plain
                # again on the next refresh.
                from PyQt5.QtGui import QBrush
                w.setBackground(QBrush())
                w.setForeground(QBrush(QColor(t("fg"))))
        else:
            w.setText(text)
            if color:
                w.setStyleSheet(f"background:{color}; color:{fg}; padding:3px 6px; "
                                  f"border:1px solid {t('border')}; font-family:Consolas;")

    # ────────────────────── Topbar handlers ──────────────────────
    def _on_lang_change(self):
        """Switch UI language by rebuilding everything with translated labels."""
        code = self._lang_box.currentData() or "en"
        if code == i18n.current(): return
        debug_log.info(f"language → {code}", "settings")
        i18n.set_lang(code)
        auth_store.set_pref("lang", code)
        # Layout direction follows language — Arabic prefers right-to-left.
        from PyQt5.QtCore import Qt as _Qt
        from PyQt5.QtWidgets import QApplication as _QApp
        _QApp.instance().setLayoutDirection(
            _Qt.RightToLeft if code == "ar" else _Qt.LeftToRight)
        self.setWindowTitle(i18n.s("AppName"))
        # Reuse the theme rebuild path — same surgery (disconnect, _build,
        # reconnect, replay state) is exactly what we need for a language flip.
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Tear down the central widget and rebuild it. Used by both
        theme + language switchers."""
        cur_view = "main"
        try:
            cw = self.view_stack.currentWidget()
            if   cw is self.page_main:     cur_view = "main"
            elif cw is self.page_band:     cur_view = "band"
            elif cw is self.page_advance:  cur_view = "advance"
            elif cw is self.page_settings: cur_view = "settings"
            elif cw is self.page_ipscan:   cur_view = "ipscan"
            elif cw is self.page_atcmd:    cur_view = "atcmd"
        except Exception: pass
        # Stop any active IP-scan workers before tearing the page down.
        try: self._ipscan_stop_all()
        except Exception: pass
        try: self.hub.updated.disconnect(self._on_data)
        except Exception: pass
        try: self.hub.auth_status.disconnect(self._on_auth)
        except Exception: pass
        self._build()
        self.hub.updated.connect(self._on_data)
        self.hub.auth_status.connect(self._on_auth)
        try:
            if getattr(self.hub.client, "logged_in", False):
                self._on_auth(True, "Connected")
        except Exception: pass
        try: self._on_data(self.hub.state)
        except Exception: pass
        self._show_view(cur_view)

    def _on_theme_change(self):
        """Switch theme: update palette + QSS, then rebuild the UI."""
        from PyQt5.QtWidgets import QApplication
        code = self._theme_box.currentData() or "light"
        if code == theme_mod.current(): return
        debug_log.info(f"theme → {code}", "settings")
        theme_mod.set_theme(code)
        auth_store.set_pref("theme", code)
        qss = theme_mod.app_qss()
        app = QApplication.instance()
        theme_mod.apply_palette(app)
        app.setStyleSheet(qss)
        self.setStyleSheet(qss)
        self._rebuild_ui()

    def _on_restart_router(self):
        if QMessageBox.question(self, "Restart Router",
                                  "Reboot the router now? Connection will drop ~60s.",
                                  QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try: rapi.reboot_device(self.hub.client)
        except Exception: pass

    def _on_logout(self):
        if QMessageBox.question(self, "Logout",
                                  "Sign out and clear saved credentials?",
                                  QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        debug_log.info("user logged out", "auth")
        auth_store.clear_credentials()
        try: self._ipscan_stop_all()
        except Exception: pass
        try: self.hub.stop()
        except Exception: pass
        # Re-prompt login
        from shared.login_view import LoginDialog
        from PyQt5.QtWidgets import QDialog
        dlg = LoginDialog()
        if dlg.exec_() != QDialog.Accepted or not dlg.accepted_data:
            self.close(); return
        u, p, remember = dlg.accepted_data
        if remember: auth_store.save_credentials(u, p)
        # Rebuild hub with new creds
        from shared.data_hub import DataHub
        self.hub = DataHub(user=u, pwd=p)
        self.hub.updated.connect(self._on_data)
        self.hub.auth_status.connect(self._on_auth)
        self.hub.start()
        self._user_chip.setText(f"👤  {u}")

    # ────────────────────── View switching ──────────────────────
    def _show_view(self, name):
        debug_log.info(f"view switch → {name}", "nav")
        if name == "main":
            self.view_stack.setCurrentWidget(self.page_main)
            self._top_btns["Main"].setChecked(True)
        elif name == "band":
            self.view_stack.setCurrentWidget(self.page_band)
            self._top_btns["Band Select"].setChecked(True)
            QTimer.singleShot(150, self._band_refresh)
            QTimer.singleShot(160, self._cell_refresh)
        elif name == "advance":
            self.view_stack.setCurrentWidget(self.page_advance)
            self._top_btns["Advance"].setChecked(True)
            QTimer.singleShot(150, self._advance_refresh)
        elif name == "settings":
            self.view_stack.setCurrentWidget(self.page_settings)
            self._top_btns["Settings"].setChecked(True)
            QTimer.singleShot(150, self._settings_refresh)
        elif name == "ipscan":
            self.view_stack.setCurrentWidget(self.page_ipscan)
            self._top_btns["IP Scan"].setChecked(True)
            QTimer.singleShot(150, self._ipscan_start_monitor)
        elif name == "atcmd":
            self.view_stack.setCurrentWidget(self.page_atcmd)
            self._top_btns["AT Command"].setChecked(True)

    # ────────────────────── Band Select page ──────────────────────
    def _build_band_page(self):
        t = theme_mod.t
        # Two distinct accent colors for LTE vs NR — derived from theme so
        # they shift with light/dark/aurora rather than staying frozen blue+green.
        acc_lte = t("accent")
        acc_nr  = t("ok") if theme_mod.current() == "light" else t("accent_2")
        # Band + Cell page laid out fluidly — no scroll. Bands grid + Cell
        # Lock card share vertical space; on small windows everything
        # compresses proportionally.
        page = QWidget()
        page.setStyleSheet(f"QWidget {{ background:{t('bg')}; }}")
        lay = QVBoxLayout(page); lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)

        # ── Hero Status Card ──
        hero = QFrame()
        hero.setStyleSheet(
            f"QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1, "
            f"stop:0 {t('card')}, stop:1 {t('card_alt')}); "
            f"border:1px solid {t('border_lt')}; border-radius:10px; }}")
        hl = QVBoxLayout(hero); hl.setContentsMargins(18, 8, 18, 8); hl.setSpacing(4)

        # title row
        ttl_row = QHBoxLayout()
        ico = QLabel("◈")
        ico.setStyleSheet(f"color:{acc_lte}; font-size:26px; font-weight:bold;")
        ttl_box = QVBoxLayout(); ttl_box.setSpacing(0)
        ttl = QLabel(i18n.s("Band Lock"))
        ttl.setStyleSheet(f"color:{acc_lte}; font-size:16px; font-weight:bold; letter-spacing:1px;")
        sub = QLabel(i18n.s("Band Lock Sub"))
        sub.setStyleSheet(f"color:{t('fg_mute')}; font-size:10px;")
        ttl_box.addWidget(ttl); ttl_box.addWidget(sub)
        ttl_row.addWidget(ico)
        ttl_row.addSpacing(10)
        ttl_row.addLayout(ttl_box)
        ttl_row.addStretch()

        # big status badge — initial neutral state, _band_refresh repaints it
        self._b_status_chip = QLabel(f"—  {i18n.s('STATUS')}")
        self._b_status_chip.setMinimumWidth(120)
        self._b_status_chip.setAlignment(Qt.AlignCenter)
        self._b_status_chip.setStyleSheet(
            f"color:{t('fg_dim')}; font-size:11px; font-weight:bold; letter-spacing:2px; "
            f"padding:6px 14px; background:{t('card_alt')}; "
            f"border:1.5px solid {t('border')}; border-radius:14px;")
        ttl_row.addWidget(self._b_status_chip)
        hl.addLayout(ttl_row)

        # divider
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background:{t('border_lt')};")
        hl.addWidget(sep)

        # currently locked rows
        locked = QHBoxLayout(); locked.setSpacing(20)
        lt_box = QVBoxLayout(); lt_box.setSpacing(4)
        lt_lbl = QLabel(i18n.s("4G LTE Currently Locked"))
        lt_lbl.setStyleSheet(f"color:{t('fg')}; font-size:11px; font-weight:bold; letter-spacing:1px;")
        lt_box.addWidget(lt_lbl)
        self._b_lte_chips = QHBoxLayout(); self._b_lte_chips.setSpacing(6); self._b_lte_chips.setAlignment(Qt.AlignLeft)
        lt_chips_w = QWidget(); lt_chips_w.setLayout(self._b_lte_chips)
        lt_box.addWidget(lt_chips_w)
        nr_box = QVBoxLayout(); nr_box.setSpacing(4)
        nr_lbl = QLabel(i18n.s("5G NR Currently Locked"))
        nr_lbl.setStyleSheet(f"color:{t('fg')}; font-size:11px; font-weight:bold; letter-spacing:1px;")
        nr_box.addWidget(nr_lbl)
        self._b_nr_chips = QHBoxLayout(); self._b_nr_chips.setSpacing(6); self._b_nr_chips.setAlignment(Qt.AlignLeft)
        nr_chips_w = QWidget(); nr_chips_w.setLayout(self._b_nr_chips)
        nr_box.addWidget(nr_chips_w)
        locked.addLayout(lt_box, 1)
        vsep = QFrame(); vsep.setFixedWidth(1); vsep.setStyleSheet(f"background:{t('border_lt')};")
        locked.addWidget(vsep)
        locked.addLayout(nr_box, 1)
        hl.addLayout(locked)
        lay.addWidget(hero)

        # ── Two large band cards ──
        cards = QHBoxLayout(); cards.setSpacing(14)

        def _band_card(title, accent, count_label, bands, prefix, store_dict_attr):
            card = QFrame()
            card.setStyleSheet(f"QFrame {{ background:{t('card')}; "
                                f"border:1px solid {t('border_lt')}; border-radius:10px; }}")
            cl = QVBoxLayout(card); cl.setContentsMargins(14, 8, 14, 12); cl.setSpacing(8)
            hdr = QHBoxLayout()
            st = QFrame(); st.setFixedSize(3, 18); st.setStyleSheet(f"background:{accent}; border-radius:2px;")
            hdr.addWidget(st); hdr.addSpacing(6)
            ti = QLabel(title); ti.setStyleSheet(f"color:{accent}; font-size:13px; font-weight:bold;")
            hdr.addWidget(ti); hdr.addStretch()
            count = QLabel(f"0 / {len(bands)}")
            count.setStyleSheet(f"color:{accent}; font-size:10px; font-weight:bold; letter-spacing:1px; "
                                 f"padding:2px 10px; background:{t('accent_bg')}; border-radius:8px;")
            hdr.addWidget(count)
            setattr(self, count_label, count)
            cl.addLayout(hdr)
            grid = QGridLayout(); grid.setHorizontalSpacing(6); grid.setVerticalSpacing(6)
            store = {}
            for i, b in enumerate(bands):
                chip = self._make_band_chip(f"{prefix}{b}", accent, t('accent_bg'))
                chip.toggled.connect(self._update_band_counts)
                store[b] = chip
                grid.addWidget(chip, i // 4, i % 4)
            setattr(self, store_dict_attr, store)
            cl.addLayout(grid)
            return card

        cards.addWidget(_band_card(i18n.s("4G LTE Bands"), acc_lte, "_b_lte_count",
                                     rapi.LTE_BANDS, "B", "_b_lte"), 1)
        cards.addWidget(_band_card(i18n.s("5G NR Bands"),  acc_nr,  "_b_nr_count",
                                     rapi.NR_BANDS,  "N", "_b_nr"), 1)
        lay.addLayout(cards, 1)

        # ── Action bar ──
        action = QFrame()
        action.setStyleSheet(f"QFrame {{ background:{t('card')}; "
                              f"border:1px solid {t('border_lt')}; border-radius:10px; }}")
        ar = QHBoxLayout(action); ar.setContentsMargins(12, 6, 12, 6); ar.setSpacing(8)

        info = QLabel(i18n.s("Modem reset note"))
        info.setStyleSheet(f"color:{t('fg_mute')}; font-size:11px;")
        ar.addWidget(info); ar.addStretch()

        btn_refresh = self._make_action_btn(i18n.s("Refresh"), t('card'), t('fg'), t('border'))
        btn_refresh.clicked.connect(self._band_refresh)
        btn_clear   = self._make_action_btn(i18n.s("Clear All"), t('card'), t('fg'), t('border'))
        btn_clear.clicked.connect(self._band_clear)
        btn_disable = self._make_action_btn(i18n.s("Disable Lock"), t('err'), "#FFFFFF", t('err'))
        btn_disable.clicked.connect(self._band_disable)
        self._b_apply_btn = self._make_action_btn(
            i18n.s("Apply & Enable"), acc_lte, "#FFFFFF", acc_lte, primary=True)
        self._b_apply_btn.clicked.connect(self._band_apply)
        for b in (btn_refresh, btn_clear, btn_disable, self._b_apply_btn):
            ar.addWidget(b)
        lay.addWidget(action)

        # ── Cell Lock section (below Band Lock, same page) ──
        lay.addWidget(self._build_cell_lock_section(t, acc_lte, acc_nr))
        return page

    # ────────────────────── Cell Lock section ──────────────────────
    def _build_cell_lock_section(self, t, acc_lte, acc_nr):
        """The cell lock pins the modem to ONE specific tower (ARFCN+PCI).
        Mutually exclusive with Band Lock — toggling one disables the other,
        per the firmware's hard rule:
            'The cell lock enable and band lock enable can't be opened
             at the same time.'"""
        # Hero
        hero = QFrame(); hero.setObjectName("ad_hero")
        hl = QVBoxLayout(hero); hl.setContentsMargins(28, 18, 28, 18); hl.setSpacing(8)
        ttl_row = QHBoxLayout()
        ico = QLabel("◧")
        ico.setStyleSheet(f"color:{acc_nr}; font-size:26px; font-weight:bold; "
                           "background:transparent;")
        box = QVBoxLayout(); box.setSpacing(0)
        ti = QLabel(i18n.s("Cell Lock"))
        ti.setStyleSheet(f"color:{acc_nr}; font-size:22px; font-weight:bold; "
                          "letter-spacing:1px; background:transparent;")
        sub = QLabel(i18n.s("Cell Lock Sub"))
        sub.setStyleSheet(f"color:{t('fg_mute')}; font-size:11px; "
                           "background:transparent;")
        box.addWidget(ti); box.addWidget(sub)
        ttl_row.addWidget(ico); ttl_row.addSpacing(10); ttl_row.addLayout(box)
        ttl_row.addStretch()

        self._cell_status_chip = QLabel(f"—  {i18n.s('STATUS')}")
        self._cell_status_chip.setMinimumWidth(150)
        self._cell_status_chip.setAlignment(Qt.AlignCenter)
        self._cell_status_chip.setStyleSheet(
            f"color:{t('fg_dim')}; font-size:14px; font-weight:bold; letter-spacing:2px; "
            f"padding:10px 20px; background:{t('card_alt')}; "
            f"border:1.5px solid {t('border')}; border-radius:22px;")
        ttl_row.addWidget(self._cell_status_chip)
        hl.addLayout(ttl_row)

        # Mutex warning — visible only when band lock is active
        self._cell_mutex_warn = QLabel("⚠  " + i18n.s("Mutex warn"))
        self._cell_mutex_warn.setWordWrap(True)
        self._cell_mutex_warn.setStyleSheet(
            f"color:{t('warn')}; background:{t('warn_bg')}; "
            f"border:1px solid {t('warn')}; border-radius:6px; "
             "padding:8px 12px; font-weight:bold;")
        self._cell_mutex_warn.setVisible(False)
        hl.addWidget(self._cell_mutex_warn)

        # Existing cells table
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background:{t('border_lt')};")
        hl.addWidget(sep)

        cells_lbl = QLabel(i18n.s("Locked Cells"))
        cells_lbl.setStyleSheet(f"color:{t('fg')}; font-size:11px; font-weight:bold; "
                                 "letter-spacing:1px; background:transparent;")
        hl.addWidget(cells_lbl)

        self._cell_table = QTableWidget(0, 4)
        self._cell_table.setHorizontalHeaderLabels([
            i18n.s("Tech"), i18n.s("ARFCN"), i18n.s("PCI"), i18n.s("Action")])
        self._cell_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._cell_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self._cell_table.verticalHeader().setVisible(False)
        self._cell_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._cell_table.setMinimumHeight(120)
        self._cell_table.setStyleSheet(
            f"QTableWidget {{ background:{t('card')}; color:{t('fg')}; "
            f"gridline-color:{t('border_lt')}; "
            f"alternate-background-color:{t('card_alt')}; "
            f"selection-background-color:{t('accent_bg')}; selection-color:{t('fg')}; }}"
            f"QHeaderView::section {{ background:{t('card_alt')}; color:{t('fg')}; "
            f"border:1px solid {t('border')}; padding:6px; font-weight:bold; }}")
        # Default rows are ~24px which clips the Delete button. We force a
        # generous row height (52px) — more than the button's 32px + the
        # 8px wrapper margin combined, so nothing can clip vertically.
        self._cell_table.verticalHeader().setDefaultSectionSize(52)
        self._cell_table.verticalHeader().setMinimumSectionSize(52)
        hl.addWidget(self._cell_table)

        # Add Cell form: Tech / ARFCN / PCI / Add button
        add_box = QFrame(); add_box.setObjectName("ad_card")
        af = QHBoxLayout(add_box); af.setContentsMargins(14, 10, 14, 10); af.setSpacing(8)
        af.addWidget(QLabel(i18n.s("Add Cell") + ":"))

        self._cell_tech_combo = QComboBox()
        self._cell_tech_combo.addItem("4G LTE", "1")
        self._cell_tech_combo.addItem("5G NR",  "2")
        af.addWidget(QLabel(i18n.s("Tech") + ":"))
        af.addWidget(self._cell_tech_combo)

        self._cell_arfcn_input = QLineEdit()
        self._cell_arfcn_input.setPlaceholderText("0–875000")
        self._cell_arfcn_input.setMaximumWidth(140)
        af.addWidget(QLabel(i18n.s("ARFCN") + ":"))
        af.addWidget(self._cell_arfcn_input)

        self._cell_pci_input = QLineEdit()
        self._cell_pci_input.setPlaceholderText("0–1007")
        self._cell_pci_input.setMaximumWidth(100)
        af.addWidget(QLabel(i18n.s("PCI") + ":"))
        af.addWidget(self._cell_pci_input)

        af.addStretch()
        btn_add = self._make_action_btn("➕  " + i18n.s("Add Cell"),
                                         acc_nr, "#FFFFFF", acc_nr, primary=True)
        btn_add.clicked.connect(self._cell_add)
        af.addWidget(btn_add)
        hl.addWidget(add_box)

        # Action bar — refresh + enable/disable toggle
        action_box = QFrame(); action_box.setObjectName("ad_card")
        ab = QHBoxLayout(action_box); ab.setContentsMargins(14, 10, 14, 10); ab.setSpacing(10)
        ab.addStretch()
        self._cell_btn_refresh = self._make_action_btn(
            i18n.s("Refresh"), t('card'), t('fg'), t('border'))
        self._cell_btn_refresh.clicked.connect(self._cell_refresh)
        ab.addWidget(self._cell_btn_refresh)

        self._cell_btn_disable = self._make_action_btn(
            i18n.s("Disable Lock"), t('err'), "#FFFFFF", t('err'))
        self._cell_btn_disable.clicked.connect(lambda: self._cell_set_enable(False))
        ab.addWidget(self._cell_btn_disable)

        self._cell_btn_enable  = self._make_action_btn(
            "✓  " + i18n.s("ENABLED"),
            acc_nr, "#FFFFFF", acc_nr, primary=True)
        self._cell_btn_enable.clicked.connect(lambda: self._cell_set_enable(True))
        ab.addWidget(self._cell_btn_enable)
        hl.addWidget(action_box)
        return hero

    def _cell_refresh(self):
        """Async — same blocking-call problem the band refresh had."""
        cl = self.hub.client
        self._async_call(lambda: rapi.get_cell_lock(cl) or {},
                          self._cell_refresh_apply)

    def _cell_refresh_apply(self, d):
        t = theme_mod.t
        if not isinstance(d, dict) or "__error__" in d:
            d = {}
        cell_on = bool(d.get("enable"))
        band_on = bool(d.get("band_lock_enable"))
        cells   = d.get("cells", []) or []

        # Status chip
        if cell_on:
            self._cell_status_chip.setText(f"●  {i18n.s('ENABLED')}")
            self._cell_status_chip.setStyleSheet(
                f"color:{t('ok')}; font-size:14px; font-weight:bold; letter-spacing:2px; "
                f"padding:10px 20px; background:{t('ok_bg')}; "
                f"border:1.5px solid {t('ok')}; border-radius:22px;")
        else:
            self._cell_status_chip.setText(f"●  {i18n.s('DISABLED')}")
            self._cell_status_chip.setStyleSheet(
                f"color:{t('fg_dim')}; font-size:14px; font-weight:bold; letter-spacing:2px; "
                f"padding:10px 20px; background:{t('card_alt')}; "
                f"border:1.5px solid {t('border')}; border-radius:22px;")

        # Mutex warning + button gating
        self._cell_mutex_warn.setVisible(band_on)
        self._cell_btn_enable.setEnabled(not band_on)
        self._cell_btn_enable.setToolTip(i18n.s("Mutex warn") if band_on else "")

        # Cells table — clear span first in case the previous render had the
        # "no cells" placeholder spanning all columns.
        try: self._cell_table.clearSpans()
        except Exception: pass
        if not cells:
            self._cell_table.setRowCount(1)
            empty = QTableWidgetItem(i18n.s("Empty cells"))
            empty.setTextAlignment(Qt.AlignCenter)
            empty.setForeground(QColor(t("fg_mute")))
            self._cell_table.setItem(0, 0, empty)
            self._cell_table.setSpan(0, 0, 1, 4)
        else:
            self._cell_table.setRowCount(len(cells))
            for r, cell in enumerate(cells):
                # Force the row height again per row — Qt has been known to
                # ignore the verticalHeader default in certain cell-widget
                # configurations, and the explicit call always wins.
                self._cell_table.setRowHeight(r, 52)
                tech = "4G LTE" if str(cell.get("act","1")) == "1" else "5G NR"
                lte_color = t("accent")
                nr_color  = t("ok") if theme_mod.current() == "light" else t("accent_2")
                tech_color = lte_color if tech.startswith("4G") else nr_color
                for c, val in enumerate([tech, str(cell.get("arfcn","")),
                                           str(cell.get("pci",""))]):
                    it = QTableWidgetItem(val)
                    it.setTextAlignment(Qt.AlignCenter)
                    if c == 0:
                        it.setForeground(QColor(tech_color))
                    self._cell_table.setItem(r, c, it)
                # Delete button — error red, fixed height that fits inside
                # the 52px row with margin to spare.
                del_btn = QPushButton("🗑  " + i18n.s("Delete"))
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setFixedHeight(32)
                del_btn.setMinimumWidth(120)
                f = QFont("Segoe UI", 10); f.setBold(True)
                del_btn.setFont(f)
                del_btn.setStyleSheet(
                    f"QPushButton {{ background:{t('err')}; color:#FFFFFF; "
                    f"border:none; border-radius:6px; padding:0 16px; }}"
                    f"QPushButton:hover {{ background:#B71C1C; }}"
                    f"QPushButton:pressed {{ background:#8E1212; }}")
                child_idx = int(cell.get("child_node_idx", r + 1))
                del_btn.clicked.connect(
                    lambda _=False, idx=child_idx: self._cell_delete(idx))
                # Centered transparent wrapper so the button doesn't stretch
                # to fill the cell AND no grey halo is painted behind it.
                cell_w = QWidget()
                cell_w.setAttribute(Qt.WA_TranslucentBackground, True)
                cell_w.setStyleSheet("background:transparent;")
                cw_lay = QHBoxLayout(cell_w)
                cw_lay.setContentsMargins(0, 0, 0, 0); cw_lay.setSpacing(0)
                cw_lay.addStretch()
                cw_lay.addWidget(del_btn, 0, Qt.AlignVCenter)
                cw_lay.addStretch()
                self._cell_table.setCellWidget(r, 3, cell_w)

    def _cell_add(self):
        try:
            arfcn = int(self._cell_arfcn_input.text().strip())
            pci   = int(self._cell_pci_input.text().strip())
        except Exception:
            QMessageBox.warning(self, i18n.s("Add Cell"),
                                  "ARFCN and PCI must be integers.")
            return
        if not (0 <= arfcn <= 875000):
            QMessageBox.warning(self, i18n.s("Add Cell"),
                                  "ARFCN must be 0–875000.")
            return
        if not (0 <= pci <= 1007):
            QMessageBox.warning(self, i18n.s("Add Cell"),
                                  "PCI must be 0–1007.")
            return
        act = self._cell_tech_combo.currentData() or "1"
        try:
            rapi.add_cell_lock_entry(self.hub.client, act, arfcn, pci)
            self._cell_arfcn_input.clear(); self._cell_pci_input.clear()
            QTimer.singleShot(500, self._cell_refresh)
        except Exception as e:
            QMessageBox.warning(self, i18n.s("Add Cell"), str(e))

    def _cell_delete(self, child_node_idx):
        if QMessageBox.question(self, i18n.s("Delete"),
                                  i18n.s("Confirm delete"),
                                  QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            rapi.del_cell_lock_entry(self.hub.client, child_node_idx)
            QTimer.singleShot(500, self._cell_refresh)
        except Exception as e:
            QMessageBox.warning(self, i18n.s("Delete"), str(e))

    def _cell_set_enable(self, enable: bool):
        try:
            rapi.set_cell_lock_enable(self.hub.client, enable)
            QTimer.singleShot(800, self._cell_refresh)
            QTimer.singleShot(800, self._band_refresh)
        except Exception as e:
            QMessageBox.warning(self, i18n.s("Cell Lock"), str(e))

    def _make_band_chip(self, label, accent_color, accent_bg):
        t = theme_mod.t
        chip = QPushButton(label)
        chip.setCheckable(True)
        chip.setMinimumHeight(32)         # was 46 — too tall for 720p
        chip.setMinimumWidth(60)
        chip.setCursor(Qt.PointingHandCursor)
        chip.setStyleSheet(f"""
            QPushButton {{
                background:{t('card_alt')}; border:1.5px solid {t('border')}; border-radius:6px;
                color:{t('fg')}; font-family:Consolas; font-size:12px; font-weight:bold;
                padding:0 6px;
            }}
            QPushButton:hover {{ background:{accent_bg}; border-color:{accent_color}; }}
            QPushButton:checked {{
                background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {accent_color}, stop:1 {accent_color});
                color:#FFFFFF; border:1.5px solid {accent_color};
            }}
        """)
        return chip

    def _make_action_btn(self, label, bg, fg, border, primary=False):
        b = QPushButton(label)
        b.setMinimumHeight(30)            # was 38
        b.setMinimumWidth(110 if primary else 95)
        b.setCursor(Qt.PointingHandCursor)
        weight = "bold" if primary else "600"
        size = "11px" if primary else "11px"
        hover_bg = theme_mod.t("topbtn_hov")
        b.setStyleSheet(f"""
            QPushButton {{
                background:{bg}; color:{fg}; border:1.5px solid {border};
                border-radius:6px; padding:0 12px;
                font-size:{size}; font-weight:{weight}; letter-spacing:0.5px;
            }}
            QPushButton:hover {{ background:{hover_bg}; }}
        """)
        return b

    def _update_band_counts(self):
        n_lte = sum(1 for c in self._b_lte.values() if c.isChecked())
        n_nr  = sum(1 for c in self._b_nr.values()  if c.isChecked())
        self._b_lte_count.setText(f"{n_lte} / {len(rapi.LTE_BANDS)}")
        self._b_nr_count.setText(f"{n_nr} / {len(rapi.NR_BANDS)}")

    def _set_locked_chips(self, layout, bands, accent_color, prefix):
        t = theme_mod.t
        while layout.count():
            it = layout.takeAt(0)
            w = it.widget()
            if w: w.deleteLater()
        if not bands:
            empty = QLabel(i18n.s("— none —"))
            empty.setStyleSheet(f"color:{t('fg_mute')}; font-size:12px; font-style:italic;")
            layout.addWidget(empty)
            return
        for b in bands:
            chip = QLabel(f"{prefix}{b}")
            chip.setStyleSheet(
                f"color:#FFFFFF; font-size:12px; font-family:Consolas; font-weight:bold; "
                f"padding:4px 14px; background:{accent_color}; border-radius:11px;")
            layout.addWidget(chip)

    def _band_refresh(self):
        """Async — pulling band-lock state on the GUI thread froze the
        window for 2-5s on slow LANs."""
        cl = self.hub.client
        self._async_call(lambda: rapi.get_band_lock(cl), self._band_refresh_apply)

    def _band_refresh_apply(self, d):
        t = theme_mod.t
        if not isinstance(d, dict) or "__error__" in d:
            self._b_status_chip.setText("●  ERROR")
            return
        en       = d.get("enable", False)
        cell_on  = bool(d.get("cell_lock_enable"))
        # Gate the band "Apply & Enable" button while cell lock is on —
        # firmware refuses to enable both at the same time anyway.
        if hasattr(self, "_b_apply_btn"):
            self._b_apply_btn.setEnabled(not cell_on)
            self._b_apply_btn.setToolTip(i18n.s("Mutex warn") if cell_on else "")
        if en:
            self._b_status_chip.setText(f"●  {i18n.s('ENABLED')}")
            self._b_status_chip.setStyleSheet(
                f"color:{t('ok')}; font-size:14px; font-weight:bold; letter-spacing:2px; "
                f"padding:10px 20px; background:{t('ok_bg')}; "
                f"border:1.5px solid {t('ok')}; border-radius:22px;")
        else:
            self._b_status_chip.setText(f"●  {i18n.s('DISABLED')}")
            self._b_status_chip.setStyleSheet(
                f"color:{t('fg_dim')}; font-size:14px; font-weight:bold; letter-spacing:2px; "
                f"padding:10px 20px; background:{t('card_alt')}; "
                f"border:1.5px solid {t('border')}; border-radius:22px;")

        lte = [b for b in (d.get("lte_locked","") or "").split(",") if b]
        nr  = [b for b in (d.get("nr_locked","")  or "").split(",") if b]

        for b, chip in self._b_lte.items(): chip.setChecked(b in lte)
        for b, chip in self._b_nr.items():  chip.setChecked(b in nr)

        # Active locked-bands strips: use the same accent the cards used
        acc_lte = t("accent")
        acc_nr  = t("ok") if theme_mod.current() == "light" else t("accent_2")
        self._set_locked_chips(self._b_lte_chips, lte, acc_lte, "B")
        self._set_locked_chips(self._b_nr_chips,  nr,  acc_nr,  "N")
        self._update_band_counts()

    def _band_clear(self):
        for c in list(self._b_lte.values()) + list(self._b_nr.values()):
            c.setChecked(False)
        self._update_band_counts()

    def _band_apply(self):
        lte = [b for b, c in self._b_lte.items() if c.isChecked()]
        nr  = [b for b, c in self._b_nr.items()  if c.isChecked()]
        if not lte and not nr:
            QMessageBox.warning(self, "No Selection", "Select at least one band.")
            return
        msg = (
            f"Enable Band Lock with:\n\n"
            f"  4G LTE: {', '.join('B'+b for b in lte) if lte else '— (none)'}\n"
            f"  5G NR : {', '.join('N'+b for b in nr) if nr else '— (none)'}\n\n"
            f"⚠  Modem will reset briefly.")
        if QMessageBox.question(self, "Confirm Band Lock", msg,
                                  QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            rapi.set_band_lock(self.hub.client, True, lte_bands=lte, nr_bands=nr)
            QMessageBox.information(self, "Applied", "Band Lock applied.")
            QTimer.singleShot(3500, self._band_refresh)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _band_disable(self):
        if QMessageBox.question(self, "Disable Band Lock",
            "Disable Band Lock and revert to automatic selection?",
            QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            rapi.set_band_lock(self.hub.client, False, lte_bands=[], nr_bands=[])
            QMessageBox.information(self, "Disabled", "Band Lock disabled.")
            QTimer.singleShot(3500, self._band_refresh)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_auth(self, ok, msg):
        t = theme_mod.t
        if ok:
            self.status_lbl.setText(f"● {i18n.s('Connected')}")
            self.status_lbl.setStyleSheet(f"color:{t('ok')}; font-weight:bold; font-size:13px;")
            import time
            if self._t0 is None: self._t0 = time.time()
        else:
            self.status_lbl.setText(f"● {msg[:40]}")
            self.status_lbl.setStyleSheet(f"color:{t('warn')}; font-weight:bold; font-size:13px;")

    def _on_data(self, st):
        try:
            r = st.get("radio", {}) or {}
            h = st.get("header", {}) or {}
            s = st.get("system", {}) or {}
            t = st.get("traffic", {}) or {}
            ca = st.get("ca", {}) or {}

            # ─── Update 3 gauges (Temp / CPU / RAM) ───
            tc = rapi.temp_celsius(s.get("Modem5GTemperature"))
            self.gauge_temp.setValue(tc)

            cpu = s.get("CPUUsage")
            try:
                self.gauge_cpu.setValue(float(cpu) if cpu not in (None,"") else None)
            except Exception:
                self.gauge_cpu.setValue(None)

            mt, mf = s.get("MemoryTotal"), s.get("MemoryFree")
            if mt and mf:
                try:
                    pct = (float(mt) - float(mf)) / float(mt) * 100
                    self.gauge_ram.setValue(pct)
                except Exception:
                    self.gauge_ram.setValue(None)
            else:
                self.gauge_ram.setValue(None)

            # General Info chips — theme-aware status colors
            tk = theme_mod.t
            OK, WARN, ERR, INFO, NEU = (tk("ok_bg"), tk("warn_bg"),
                                          tk("err_bg"), tk("info_bg"), tk("card_alt"))
            wm   = r.get("WorkMode")
            conn = h.get("connetStatus")
            self._set_chip(self._conn["connstat"],
                            "connected" if conn == 1 else "disconnected",
                            OK if conn == 1 else ERR)

            # Single unified 4G+5G signal bars (router's own scale 0..5)
            try:
                lvl = int(h.get("SignalLevel") or 0)
            except Exception:
                lvl = 0
            bars = "▌" * max(0, min(5, lvl)) + "▱" * (5 - max(0, min(5, lvl)))
            sig_color = (ERR if lvl <= 1 else WARN if lvl <= 2
                          else OK if lvl <= 4 else INFO)
            self._set_chip(self._conn["signal"], f"{bars}  {lvl}/5", sig_color)

            self._set_chip(self._conn["status5g"],
                            "5G connected" if wm == "NSA" else
                            ("5G SA" if wm == "SA" else "—"),
                            OK if wm in ("NSA","SA") else NEU)

            wi = h.get("WanInterface","")
            self._set_chip(self._conn["nettype"], "5G" if "5G" in wi else "LTE")

            # NetworkMode + 5G Option (read from network_set, not from WAN interface)
            ns = (st.get("misc") or {}).get("net_set") or {}
            nm  = rapi.network_mode_label(ns.get("NetworkMode"))
            opt = rapi.endc_label(ns.get("ENDC"))
            self._set_chip(self._conn["nettypeex"],
                            f"{nm} · {opt}" if (nm or opt) else "—", OK)

            # Software Version
            sw = s.get("SoftwareVersion") or "—"
            self._set_chip(self._conn["swver"], sw, NEU)

            # Network info
            self._net["plmn"].setText(str(h.get("SIMPlmn","")))
            self._net["spn"].setText(str(h.get("SPN","")))

            # Traffic — Up/Dn Rate cells were removed from the v2 layout
            # because they flickered between "0.0 KB" and "—". The remaining
            # cells (today/total/connect-time) are stable counters.
            self._traf["up_now"].setText(rapi.fmt_bytes(t.get("TodayTotalTxBytes")))
            self._traf["dn_now"].setText(rapi.fmt_bytes(t.get("TodayTotalRxBytes")))
            self._traf["up_total"].setText(rapi.fmt_bytes(t.get("MonthTxBytes")))
            self._traf["dn_total"].setText(rapi.fmt_bytes(t.get("MonthRxBytes")))
            self._traf["conn_total"].setText(s.get("uptime_fmt","—") or "—")
            misc = st.get("misc",{}) or {}
            wan = misc.get("wan_ip",{}) if isinstance(misc, dict) else {}
            self._traf["conn_now"].setText(rapi.fmt_uptime_seconds(wan.get("Uptime")))

            # CA table
            self._fill_ca_table(ca)

            # ─── 5G NR (real values from rfSignal) ───
            def _fmt(v, unit=""):
                if v in (None, ""): return "—"
                s = str(v)
                if unit and not s.endswith(unit): return f"{s} {unit}"
                return s

            # 5G NR
            # Choose chip color from the actual signal value, not a fixed hue,
            # so weak signals look red regardless of theme.
            def _signal_color(val, kind):
                try: v = float(val)
                except Exception: return tk("card_alt")
                if kind == "rsrp":
                    return (tk("ok_bg")  if v >= -90  else
                            tk("warn_bg") if v >= -100 else
                            tk("err_bg"))
                if kind == "sinr":
                    return (tk("ok_bg")  if v >= 13 else
                            tk("warn_bg") if v >= 0  else
                            tk("err_bg"))
                if kind == "rsrq":
                    return (tk("ok_bg")  if v >= -15 else
                            tk("warn_bg") if v >= -19 else
                            tk("err_bg"))
                if kind == "rssi":
                    return (tk("ok_bg")  if v >= -75 else
                            tk("warn_bg") if v >= -85 else
                            tk("err_bg"))
                return tk("card_alt")

            self._set_chip(self._nr["band"],   f"N{r.get('NR_BAND')}" if r.get('NR_BAND') else "—")
            self._set_chip(self._nr["pci"],    r.get("NR_PCI") or r.get("PCI"))
            self._set_chip(self._nr["rsrp"],   _fmt(r.get("SSB_RSRP"), "dBm"),
                            _signal_color(r.get("SSB_RSRP"), "rsrp"))
            self._set_chip(self._nr["rsrq"],   _fmt(r.get("SSB_RSRQ"), "dB"),
                            _signal_color(r.get("SSB_RSRQ"), "rsrq"))
            self._set_chip(self._nr["sinr"],   _fmt(r.get("SSB_SINR"), "dB"),
                            _signal_color(r.get("SSB_SINR"), "sinr"))
            self._set_chip(self._nr["rssi"],   _fmt(r.get("SSB_RSSI"), "dBm"),
                            _signal_color(r.get("SSB_RSSI"), "rssi"))
            self._set_chip(self._nr["power"],  _fmt(r.get("NR_Power"), "dBm"))
            self._set_chip(self._nr["cqi"],    r.get("NR_CQI"))
            self._set_chip(self._nr["qci"],    r.get("NR_QCI"))
            self._set_chip(self._nr["cellid"], r.get("NCGI"))

            # 4G LTE
            self._set_chip(self._lte["band"],   f"B{r.get('BAND')}" if r.get('BAND') else "—")
            self._set_chip(self._lte["pci"],    r.get("PCI"))
            self._set_chip(self._lte["rsrp"],   _fmt(r.get("RSRP"), "dBm"),
                            _signal_color(r.get("RSRP"), "rsrp"))
            self._set_chip(self._lte["rsrq"],   _fmt(r.get("RSRQ"), "dB"),
                            _signal_color(r.get("RSRQ"), "rsrq"))
            self._set_chip(self._lte["sinr"],   _fmt(r.get("SINR"), "dB"),
                            _signal_color(r.get("SINR"), "sinr"))
            self._set_chip(self._lte["rssi"],   _fmt(r.get("RSSI"), "dBm"),
                            _signal_color(r.get("RSSI"), "rssi"))
            self._set_chip(self._lte["power"],  _fmt(r.get("LTE_Power"), "dBm"))
            self._set_chip(self._lte["cqi"],    r.get("LTE_CQI"))
            self._set_chip(self._lte["qci"],    r.get("QCI"))
            self._set_chip(self._lte["cellid"], r.get("ECGI"))

            # ── Live zone charts (4G + 5G, separate per metric) ──
            for v, zc in [(r.get("RSRP"), self.zc_4g_rsrp),
                          (r.get("RSSI"), self.zc_4g_rssi),
                          (r.get("RSRQ"), self.zc_4g_rsrq),
                          (r.get("SINR"), self.zc_4g_sinr),
                          (r.get("SSB_RSRP"), self.zc_5g_rsrp),
                          (r.get("SSB_RSSI"), self.zc_5g_rssi),
                          (r.get("SSB_RSRQ"), self.zc_5g_rsrq),
                          (r.get("SSB_SINR"), self.zc_5g_sinr)]:
                if v not in (None, ""):
                    try: zc.addPoint(v)
                    except Exception: pass
        except Exception:
            pass

    def _fill_ca_table(self, ca):
        """Fill CA table — only 6 rows (Type → DL_BandWidth)."""
        def _conv(s):
            """Type column: keep only the technology — '4G' or '5G'."""
            if s is None: return "—"
            t = str(s).upper()
            if "LTE" in t: return "4G"
            if "NR" in t:  return "5G"
            return str(s)

        def _clean(v):
            if v in (None, ""): return "—"
            s = str(v)
            if s in ("255","<unknown bandwidth>","<unknown modulation>"): return "—"
            return s

        pcc1 = ca.get("pcc1") or {}
        pcc2 = ca.get("pcc2") or {}
        # Drop firmware placeholder rows AND deactivated SCCs at the source.
        # Router emits stale band data for SCCs after they go inactive,
        # so trusting SCC_State as the only filter is the safe path.
        def _scc_is_active(s):
            t  = str(s.get("SCC_Type", "") or "").strip()
            b  = str(s.get("SCC_Band", "") or "").strip()
            st = str(s.get("SCC_State", "") or "").strip().lower()
            return (t and t not in ("-", "—") and
                    b and b not in ("-", "—") and
                    st in ("activated", "actived"))
        sccs = [s for s in (ca.get("sccs") or []) if _scc_is_active(s)]

        def pcc_vals(p, prefix="pcc"):
            return {
                "Type":        p.get(f"{prefix}Type"),
                "State":       "activated" if p.get(f"{prefix}Type") not in (None,"","-") else "—",
                "Band":        p.get(f"{prefix}Band"),
                "PCI":         p.get(f"{prefix}Pci"),
                "Arfcn":       p.get(f"{prefix}Arfcn"),
                "DL_BandWidth":p.get(f"{prefix}DlBandWidth"),
            }

        def scc_vals(s):
            return {
                "Type":        s.get("SCC_Type"),
                "State":       s.get("SCC_State"),
                "Band":        s.get("SCC_Band"),
                "PCI":         s.get("SCC_Pci"),
                "Arfcn":       s.get("SCC_Arfcn"),
                "DL_BandWidth":s.get("SCC_DlBandWidth"),
            }

        cols_data = [
            (1, pcc_vals(pcc1) if pcc1 else None),
            (2, pcc_vals(pcc2) if pcc2 else None),
            (3, scc_vals(sccs[0]) if len(sccs) > 0 else None),
            (4, scc_vals(sccs[1]) if len(sccs) > 1 else None),
            (5, scc_vals(sccs[2]) if len(sccs) > 2 else None),
        ]

        # Hide column unless we have data AND state is actively confirmed.
        for col, vals in cols_data:
            hide = vals is None
            self.ca_table.setColumnHidden(col, hide)

        for r, param in enumerate(self._ca_params):
            for col, vals in cols_data:
                if vals is None:
                    text = "—"; color = QColor("#BBB")
                else:
                    raw = vals.get(param)
                    text = _clean(raw)
                    if param == "Type":
                        text = _conv(raw)
                        color = QColor("#1565C0") if "5G" in text else QColor("#E65100")
                    elif param == "State":
                        if text in ("activated","actived"): color = QColor("#2E7D32")
                        elif text == "deactivated":         color = QColor("#C62828")
                        else: color = QColor("#666")
                    elif param == "Band":  color = QColor("#2E7D32")
                    elif param == "PCI":   color = QColor("#1565C0")
                    elif text == "—":      color = QColor("#AAA")
                    else:                  color = QColor("#333")
                it = QTableWidgetItem(text)
                it.setTextAlignment(Qt.AlignCenter)
                it.setForeground(color)
                if param == "Type" and text != "—":
                    f = QFont("Consolas", 9, QFont.Bold); it.setFont(f)
                self.ca_table.setItem(r, col, it)

    # ────────────────────── Advance page ──────────────────────
    def _build_advance_page(self):
        """Cellular advanced settings — toggles and modes for the SIM/network."""
        page = QWidget()
        page.setStyleSheet(f"QWidget {{ background:{theme_mod.t('bg')}; }}")
        # No scroll — content fits via compact card layout.
        lay = QVBoxLayout(page); lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)

        # Hero header
        hero = self._adv_hero(i18n.s("Advanced Cellular Settings"), i18n.s("Adv sub"))
        lay.addWidget(hero)

        # Refresh button row
        bar = QHBoxLayout(); bar.setContentsMargins(0, 0, 0, 0)
        self._adv_status = QLabel(i18n.s("Loading…"))
        self._adv_status.setStyleSheet(
            f"color:{theme_mod.t('fg_mute')}; font-size:11px; background:transparent;")
        bar.addWidget(self._adv_status); bar.addStretch()
        ref = QPushButton(i18n.s("Refresh")); ref.setObjectName("topbtn")
        ref.setStyleSheet(self._adv_btn_style())
        ref.clicked.connect(self._advance_refresh)
        bar.addWidget(ref)
        lay.addLayout(bar)

        # 2-col grid of cards
        grid = QGridLayout(); grid.setSpacing(14); grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)

        grid.addWidget(self._adv_card_airplane(), 0, 0)
        grid.addWidget(self._adv_card_netmode(),  0, 1)
        grid.addWidget(self._adv_card_cellular(), 1, 0)
        grid.addWidget(self._adv_card_ca(),       1, 1)
        grid.addWidget(self._adv_card_antenna(),  2, 0)
        grid.addWidget(self._adv_card_sms(),      2, 1)
        grid.addWidget(self._adv_card_volte(),    3, 0)

        lay.addLayout(grid)
        # Full-width card
        lay.addWidget(self._adv_card_traffic())
        lay.addStretch()
        return page

    # ── Card helpers ──
    # Compact heights / paddings so cards fit on 720p without forcing a
    # scrollbar. Inline parent stylesheets are avoided (they break form-
    # widget rendering); object names route styling through app QSS instead.
    def _adv_hero(self, title, sub):
        t = theme_mod.t
        hero = QFrame(); hero.setObjectName("ad_hero")
        h = QHBoxLayout(hero); h.setContentsMargins(18, 8, 18, 8); h.setSpacing(8)
        ico = QLabel("⚙"); ico.setStyleSheet(
            f"color:{t('accent')}; font-size:20px; font-weight:bold; background:transparent;")
        box = QVBoxLayout(); box.setSpacing(0)
        ti = QLabel(title); ti.setStyleSheet(
            f"color:{t('accent')}; font-size:16px; font-weight:bold; "
            "letter-spacing:1px; background:transparent;")
        s = QLabel(sub); s.setStyleSheet(
            f"color:{t('fg_mute')}; font-size:10px; background:transparent;")
        box.addWidget(ti); box.addWidget(s)
        h.addWidget(ico); h.addSpacing(6); h.addLayout(box); h.addStretch()
        return hero

    def _adv_card(self, title, icon="◆", color=None):
        t = theme_mod.t
        if color is None: color = t("accent")
        card = QFrame(); card.setObjectName("ad_card")
        v = QVBoxLayout(card); v.setContentsMargins(14, 8, 14, 10); v.setSpacing(6)
        hdr = QHBoxLayout()
        st = QFrame(); st.setFixedSize(3, 18)
        st.setStyleSheet(f"background:{color}; border-radius:2px; border:none;")
        hdr.addWidget(st); hdr.addSpacing(6)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color:{color}; font-size:12px; font-weight:bold; background:transparent;")
        hdr.addWidget(lbl); hdr.addStretch()
        v.addLayout(hdr)
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{t('border_lt')}; border:none;")
        v.addWidget(sep)
        return card, v

    def _adv_btn_style(self, primary=False):
        t = theme_mod.t
        if primary:
            return (f"QPushButton {{ background:{t('accent')}; color:#FFFFFF; border:none; "
                    f"border-radius:4px; padding:8px 18px; font-weight:bold; font-size:12px; }}"
                    f"QPushButton:hover {{ background:{t('accent_2')}; }}")
        return (f"QPushButton {{ background:{t('card')}; color:{t('accent')}; "
                f"border:1px solid {t('accent')}; border-radius:4px; padding:6px 14px; "
                f"font-weight:bold; font-size:11px; }}"
                f"QPushButton:hover {{ background:{t('accent_bg')}; }}")

    def _adv_row(self, label, widget):
        row = QHBoxLayout()
        l = QLabel(label)
        l.setStyleSheet(f"color:{theme_mod.t('fg')}; font-size:12px; "
                         "background:transparent;")
        l.setMinimumWidth(150)
        row.addWidget(l); row.addWidget(widget, 1)
        return row

    def _adv_card_netmode(self):
        card, v = self._adv_card(i18n.s("Network Mode + 5G Option"), color="#0D47A1")
        self._adv_w = getattr(self, "_adv_w", {})
        self._adv_w["netmode"] = QComboBox()
        for code, lbl in [("0","4G Only"),("2","5G Only"),
                           ("3","5G Pref"),("4","3G Only(WCDMA)")]:
            self._adv_w["netmode"].addItem(lbl, code)
        self._adv_w["endc"] = QComboBox()
        for code, lbl in [("1","SA"),("2","NSA"),("3","SA+NSA")]:
            self._adv_w["endc"].addItem(lbl, code)
        v.addLayout(self._adv_row(i18n.s("Network Mode"),  self._adv_w["netmode"]))
        v.addLayout(self._adv_row(i18n.s("5G Option"),     self._adv_w["endc"]))
        v.addStretch()
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._adv_apply_netmode)
        bar = QHBoxLayout(); bar.addStretch(); bar.addWidget(b); v.addLayout(bar)
        return card

    def _adv_card_airplane(self):
        """Standalone instant-toggle. One click flips the cellular radio
        without an Apply button — matches the user's mental model of an
        airplane switch on the device itself."""
        card, v = self._adv_card(i18n.s("Airplane Mode"), color="#E65100")
        self._adv_w = getattr(self, "_adv_w", {})
        self._adv_w["airplane_btn"] = b = QPushButton(i18n.s("AIRPLANE: OFF"))
        b.setMinimumHeight(40)
        b.setStyleSheet(self._airplane_btn_style(False))
        b.clicked.connect(self._adv_toggle_airplane)
        v.addWidget(b)
        hint = QLabel(i18n.s("Airplane hint"))
        hint.setStyleSheet(
            f"color:{theme_mod.t('fg_mute')}; font-size:11px; background:transparent;")
        hint.setAlignment(Qt.AlignCenter)
        v.addWidget(hint); v.addStretch()
        return card

    def _airplane_btn_style(self, on: bool) -> str:
        t = theme_mod.t
        if on:
            return (f"QPushButton {{ background:{t('warn')}; color:#FFFFFF; border:none; "
                     "border-radius:5px; font-size:13px; font-weight:bold; letter-spacing:1px; }}"
                    f"QPushButton:hover {{ background:{t('err')}; }}")
        return (f"QPushButton {{ background:{t('card_alt')}; color:{t('fg')}; "
                f"border:1px solid {t('border')}; border-radius:5px; "
                 "font-size:13px; font-weight:bold; letter-spacing:1px; }}"
                f"QPushButton:hover {{ background:{t('topbtn_hov')}; }}")

    def _adv_card_cellular(self):
        card, v = self._adv_card(i18n.s("Roaming"), color="#00838F")
        self._adv_w["roaming"]  = QCheckBox(i18n.s("Roaming Enabled"))
        v.addWidget(self._adv_w["roaming"]); v.addStretch()
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._adv_apply_roaming)
        bar = QHBoxLayout(); bar.addStretch(); bar.addWidget(b); v.addLayout(bar)
        return card

    def _adv_card_ca(self):
        card, v = self._adv_card(i18n.s("Carrier Aggregation"), color="#2E7D32")
        self._adv_w["ca"] = QCheckBox(i18n.s("Enable Carrier Aggregation"))
        v.addWidget(self._adv_w["ca"])
        v.addStretch()
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._adv_apply_ca)
        bar = QHBoxLayout(); bar.addStretch(); bar.addWidget(b); v.addLayout(bar)
        return card

    def _adv_card_antenna(self):
        card, v = self._adv_card(i18n.s("5G NR External Antenna"), color="#6A1B9A")
        self._adv_w["ant_sw"] = QCheckBox(i18n.s("Enable External Antenna"))
        self._adv_w["ant_band"] = QComboBox()
        for code, lbl in [("2","N78"),("1","N77")]:
            self._adv_w["ant_band"].addItem(lbl, code)
        v.addWidget(self._adv_w["ant_sw"])
        v.addLayout(self._adv_row(i18n.s("Working Band"), self._adv_w["ant_band"]))
        v.addStretch()
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._adv_apply_antenna)
        bar = QHBoxLayout(); bar.addStretch(); bar.addWidget(b); v.addLayout(bar)
        return card

    def _adv_card_sms(self):
        card, v = self._adv_card(i18n.s("SMS Switch"), color="#EF6C00")
        self._adv_w["sms"] = QCheckBox(i18n.s("Enable SMS Service"))
        v.addWidget(self._adv_w["sms"]); v.addStretch()
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._adv_apply_sms)
        bar = QHBoxLayout(); bar.addStretch(); bar.addWidget(b); v.addLayout(bar)
        return card

    def _adv_card_volte(self):
        card, v = self._adv_card(i18n.s("VoLTE"), color="#AD1457")
        self._adv_w["volte"] = QCheckBox(i18n.s("Enable VoLTE"))
        v.addWidget(self._adv_w["volte"]); v.addStretch()
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._adv_apply_volte)
        bar = QHBoxLayout(); bar.addStretch(); bar.addWidget(b); v.addLayout(bar)
        return card

    def _adv_card_traffic(self):
        card, v = self._adv_card(i18n.s("Traffic Control"), color="#C62828")
        # Daily row
        d_row = QHBoxLayout()
        self._adv_w["day_sw"] = QCheckBox(i18n.s("Daily Limit"))
        self._adv_w["day_in"] = QSpinBox(); self._adv_w["day_in"].setRange(0, 1024*1024)
        self._adv_w["day_in"].setSuffix(" MB"); self._adv_w["day_in"].setMinimumWidth(140)
        d_row.addWidget(self._adv_w["day_sw"]); d_row.addSpacing(10)
        d_row.addWidget(QLabel(i18n.s("Threshold:")))
        d_row.addWidget(self._adv_w["day_in"]); d_row.addStretch()
        v.addLayout(d_row)
        # Monthly row
        m_row = QHBoxLayout()
        self._adv_w["mon_sw"] = QCheckBox(i18n.s("Monthly Limit"))
        self._adv_w["mon_in"] = QSpinBox(); self._adv_w["mon_in"].setRange(0, 100000)
        self._adv_w["mon_in"].setSuffix(" GB"); self._adv_w["mon_in"].setMinimumWidth(140)
        m_row.addWidget(self._adv_w["mon_sw"]); m_row.addSpacing(10)
        m_row.addWidget(QLabel(i18n.s("Threshold:")))
        m_row.addWidget(self._adv_w["mon_in"]); m_row.addStretch()
        v.addLayout(m_row)
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._adv_apply_traffic)
        bar = QHBoxLayout(); bar.addStretch(); bar.addWidget(b); v.addLayout(bar)
        return card

    # ── Refresh & Apply handlers ──
    def _advance_refresh(self):
        """Async — get_advance does a multipost (single round-trip) but
        even one round-trip on a slow VM blocks the GUI for 1-3s."""
        cl = self.hub.client
        self._adv_status.setText(i18n.s("Loading…"))
        self._async_call(lambda: rapi.get_advance(cl) or {},
                          self._advance_refresh_apply)

    def _advance_refresh_apply(self, d):
        if not isinstance(d, dict) or "__error__" in d:
            self._adv_status.setText("Load failed")
            self._adv_status.setStyleSheet(
                f"color:{theme_mod.t('err')}; font-size:11px; background:transparent;")
            return
        try:
            self._adv_w["netmode"].setCurrentIndex(
                self._adv_w["netmode"].findData(str(d.get("NetworkMode") or "3")))
            self._adv_w["endc"].setCurrentIndex(
                self._adv_w["endc"].findData(str(d.get("ENDC") or "3")))
            ap_on = str(d.get("AirplaneEnable")) == "1"
            self._adv_w["airplane_btn"].setText(
                i18n.s("AIRPLANE: ON" if ap_on else "AIRPLANE: OFF"))
            self._adv_w["airplane_btn"].setStyleSheet(self._airplane_btn_style(ap_on))
            self._adv_w["airplane_btn"].setProperty("on", ap_on)
            self._adv_w["roaming"].setChecked(str(d.get("RoamingEnable")) == "1")
            self._adv_w["ca"].setChecked(str(d.get("CaEnable")) == "1")
            self._adv_w["ant_sw"].setChecked(str(d.get("AntennaSwitch")) == "1")
            self._adv_w["ant_band"].setCurrentIndex(
                self._adv_w["ant_band"].findData(str(d.get("AntennaType") or "2")))
            self._adv_w["sms"].setChecked(str(d.get("SmsDisable")) == "0")
            self._adv_w["volte"].setChecked(str(d.get("VolteSwitch")) == "1")
            self._adv_w["day_sw"].setChecked(str(d.get("DayTrafSwitch")) == "1")
            self._adv_w["mon_sw"].setChecked(str(d.get("MonthTrafSwitch")) == "1")
            try:
                self._adv_w["day_in"].setValue(int(int(d.get("DayTrafBytes") or 0) / 1048576))
            except Exception: pass
            try:
                self._adv_w["mon_in"].setValue(int(int(d.get("MonthTrafBytes") or 0) / 1073741824))
            except Exception: pass
            import time
            self._adv_status.setText(f"Loaded · {time.strftime('%H:%M:%S')}")
            self._adv_status.setStyleSheet("color:#2E7D32; font-size:11px;")
        except Exception as e:
            self._adv_status.setText(f"Load failed: {str(e)[:60]}")
            self._adv_status.setStyleSheet("color:#C62828; font-size:11px;")

    def _adv_toast(self, ok, msg=""):
        self._adv_status.setText(("✓ " if ok else "✗ ") + (msg or ""))
        self._adv_status.setStyleSheet(
            f"color:{'#2E7D32' if ok else '#C62828'}; font-size:11px; font-weight:bold;")
        QTimer.singleShot(2400, self._advance_refresh)

    def _adv_apply_netmode(self):
        try:
            nm = self._adv_w["netmode"].currentData()
            ec = self._adv_w["endc"].currentData()
            debug_log.info(f"set network_mode={nm}, endc={ec}", "advance")
            rapi.set_network_mode(self.hub.client, nm, ec)
            self._adv_toast(True, f"Network Mode = {self._adv_w['netmode'].currentText()} · "
                                   f"5G Option = {self._adv_w['endc'].currentText()}")
        except Exception as e:
            debug_log.exc(f"set_network_mode failed: {e}", "advance")
            self._adv_toast(False, str(e)[:60])

    def _adv_toggle_airplane(self):
        """One-click flip — read current state from button property."""
        try:
            cur = bool(self._adv_w["airplane_btn"].property("on"))
            new = not cur
            debug_log.info(f"airplane → {'ON' if new else 'OFF'}", "advance")
            rapi.set_airplane(self.hub.client, new)
            self._adv_w["airplane_btn"].setText(
                i18n.s("AIRPLANE: ON" if new else "AIRPLANE: OFF"))
            self._adv_w["airplane_btn"].setStyleSheet(self._airplane_btn_style(new))
            self._adv_w["airplane_btn"].setProperty("on", new)
            self._adv_toast(True, f"Airplane Mode {'ENABLED' if new else 'DISABLED'}")
        except Exception as e: self._adv_toast(False, str(e)[:60])

    def _adv_apply_roaming(self):
        try:
            rapi.set_roaming(self.hub.client, self._adv_w["roaming"].isChecked())
            self._adv_toast(True, "Roaming applied")
        except Exception as e: self._adv_toast(False, str(e)[:60])

    def _adv_apply_ca(self):
        try:
            rapi.set_carrier_aggregation(self.hub.client, self._adv_w["ca"].isChecked())
            self._adv_toast(True, "Carrier Aggregation applied")
        except Exception as e: self._adv_toast(False, str(e)[:60])

    def _adv_apply_antenna(self):
        try:
            rapi.set_external_antenna(self.hub.client,
                self._adv_w["ant_sw"].isChecked(),
                self._adv_w["ant_band"].currentData() or "2")
            self._adv_toast(True, "External Antenna applied")
        except Exception as e: self._adv_toast(False, str(e)[:60])

    def _adv_apply_sms(self):
        try:
            rapi.set_sms_enable(self.hub.client, self._adv_w["sms"].isChecked())
            self._adv_toast(True, "SMS switch applied")
        except Exception as e: self._adv_toast(False, str(e)[:60])

    def _adv_apply_volte(self):
        try:
            rapi.set_volte(self.hub.client, self._adv_w["volte"].isChecked())
            self._adv_toast(True, "VoLTE applied")
        except Exception as e: self._adv_toast(False, str(e)[:60])

    def _adv_apply_traffic(self):
        try:
            rapi.set_traffic_threshold(self.hub.client,
                day_on=self._adv_w["day_sw"].isChecked(),
                day_mb=self._adv_w["day_in"].value(),
                month_on=self._adv_w["mon_sw"].isChecked(),
                month_gb=self._adv_w["mon_in"].value())
            self._adv_toast(True, "Traffic limits applied")
        except Exception as e: self._adv_toast(False, str(e)[:60])


    # ────────────────────── Settings page ──────────────────────
    def _build_settings_page(self):
        """Device configuration grouped into 3 sub-tabs:
            🌐 Network   — LAN / Wi-Fi
            🔒 Security  — Firewall / ALG+UPnP / TR-069
            👤 Account   — Admin password / System actions
        Each sub-tab has 2-3 cards max so it fits any window without scroll."""
        from PyQt5.QtWidgets import QTabWidget
        t = theme_mod.t
        page = QWidget()
        page.setStyleSheet(f"QWidget {{ background:{t('bg')}; }}")
        lay = QVBoxLayout(page); lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)

        # Hero + status row
        lay.addWidget(self._adv_hero(i18n.s("Device Settings"), i18n.s("Set sub")))
        bar = QHBoxLayout()
        self._set_status = QLabel(i18n.s("Loading…"))
        self._set_status.setStyleSheet(
            f"color:{t('fg_mute')}; font-size:11px; background:transparent;")
        bar.addWidget(self._set_status); bar.addStretch()
        ref = QPushButton(i18n.s("Refresh")); ref.setStyleSheet(self._adv_btn_style())
        ref.clicked.connect(self._settings_refresh)
        bar.addWidget(ref)
        lay.addLayout(bar)

        self._set_w = {}

        # Sub-tabs container
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:1px solid {t('border_lt')};
                                 border-radius:6px; background:{t('card')}; top:-1px; }}
            QTabBar::tab {{ background:{t('card_alt')}; color:{t('fg_dim')};
                            padding:6px 16px; border:1px solid {t('border_lt')};
                            border-bottom:none; border-top-left-radius:5px;
                            border-top-right-radius:5px; margin-right:2px;
                            font-weight:bold; }}
            QTabBar::tab:selected {{ background:{t('card')}; color:{t('accent')}; }}
            QTabBar::tab:hover {{ background:{t('card')}; }}
        """)

        # ── Tab 1: Network (LAN + Wi-Fi) ──
        t1 = QWidget(); v1 = QVBoxLayout(t1)
        v1.setContentsMargins(8, 8, 8, 8); v1.setSpacing(8)
        h1 = QHBoxLayout(); h1.setSpacing(8)
        h1.addWidget(self._set_card_lan(), 1)
        h1.addWidget(self._set_card_wifi(), 1)
        v1.addLayout(h1); v1.addStretch()
        tabs.addTab(t1, "🌐  Network")

        # ── Tab 2: Security (Firewall + ALG/UPnP + TR-069) ──
        t2 = QWidget(); v2 = QVBoxLayout(t2)
        v2.setContentsMargins(8, 8, 8, 8); v2.setSpacing(8)
        h2 = QHBoxLayout(); h2.setSpacing(8)
        h2.addWidget(self._set_card_firewall(), 1)
        h2.addWidget(self._set_card_alg_upnp(), 1)
        v2.addLayout(h2)
        v2.addWidget(self._set_card_acs())
        v2.addStretch()
        tabs.addTab(t2, "🔒  Security")

        # ── Tab 3: Account & System ──
        t3 = QWidget(); v3 = QVBoxLayout(t3)
        v3.setContentsMargins(8, 8, 8, 8); v3.setSpacing(8)
        v3.addWidget(self._set_card_account())
        v3.addWidget(self._set_card_system())
        v3.addStretch()
        tabs.addTab(t3, "👤  Account")

        lay.addWidget(tabs, 1)
        return page

    # ── Settings cards ──
    def _set_card_lan(self):
        card, v = self._adv_card(i18n.s("LAN / IPv4"), color="#0277BD")
        w = self._set_w
        w["ip"]   = QLineEdit(); w["ip"].setPlaceholderText("192.168.8.1")
        w["mask"] = QLineEdit(); w["mask"].setPlaceholderText("255.255.255.0")
        w["dhcp"] = QCheckBox(i18n.s("DHCP Server"))
        w["dmin"] = QLineEdit(); w["dmin"].setPlaceholderText("192.168.8.100")
        w["dmax"] = QLineEdit(); w["dmax"].setPlaceholderText("192.168.8.200")
        w["lease"] = QSpinBox(); w["lease"].setRange(60, 604800)
        w["lease"].setSuffix(" sec"); w["lease"].setMinimumWidth(120)
        v.addLayout(self._adv_row(i18n.s("LAN IP"),       w["ip"]))
        v.addLayout(self._adv_row(i18n.s("Subnet Mask"),  w["mask"]))
        v.addWidget(w["dhcp"])
        v.addLayout(self._adv_row(i18n.s("DHCP Start"),   w["dmin"]))
        v.addLayout(self._adv_row(i18n.s("DHCP End"),     w["dmax"]))
        v.addLayout(self._adv_row(i18n.s("Lease"),        w["lease"]))
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._set_apply_lan)
        bb = QHBoxLayout(); bb.addStretch(); bb.addWidget(b); v.addLayout(bb)
        return card

    def _set_card_wifi(self):
        card, v = self._adv_card(i18n.s("Wi-Fi (Primary SSIDs)"), color="#00838F")
        w = self._set_w
        # SSID 1
        w["s1_en"] = QCheckBox(i18n.s("Enable SSID-1"))
        w["s1_name"] = QLineEdit(); w["s1_name"].setPlaceholderText("FA")
        w["s1_pwd"]  = QLineEdit(); w["s1_pwd"].setPlaceholderText("password (leave blank to keep)")
        w["s1_pwd"].setEchoMode(QLineEdit.Password)
        v.addWidget(w["s1_en"])
        v.addLayout(self._adv_row(i18n.s("SSID-1 Name"), w["s1_name"]))
        v.addLayout(self._adv_row(i18n.s("SSID-1 Pwd"),  w["s1_pwd"]))
        # SSID 2 (commonly 5G primary or guest)
        sp = QFrame(); sp.setFixedHeight(1)
        sp.setStyleSheet(f"background:{theme_mod.t('border_lt')}; border:none;")
        v.addWidget(sp)
        w["s2_en"] = QCheckBox(i18n.s("Enable SSID-2"))
        w["s2_name"] = QLineEdit()
        w["s2_pwd"]  = QLineEdit(); w["s2_pwd"].setEchoMode(QLineEdit.Password)
        v.addWidget(w["s2_en"])
        v.addLayout(self._adv_row(i18n.s("SSID-2 Name"), w["s2_name"]))
        v.addLayout(self._adv_row(i18n.s("SSID-2 Pwd"),  w["s2_pwd"]))
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._set_apply_wifi)
        bb = QHBoxLayout(); bb.addStretch(); bb.addWidget(b); v.addLayout(bb)
        return card

    def _set_card_firewall(self):
        card, v = self._adv_card(i18n.s("Firewall"), color="#D32F2F")
        w = self._set_w
        w["fw_lvl"] = QComboBox()
        for code, lbl in [("0","Off"),("1","Low"),("2","Medium"),("3","High")]:
            w["fw_lvl"].addItem(lbl, code)
        v.addLayout(self._adv_row(i18n.s("Firewall Level"), w["fw_lvl"]))
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._set_apply_firewall)
        bb = QHBoxLayout(); bb.addStretch(); bb.addWidget(b); v.addLayout(bb)
        return card

    def _set_card_alg_upnp(self):
        card, v = self._adv_card(i18n.s("ALG + UPnP"), color="#7B1FA2")
        w = self._set_w
        w["l2tp"]  = QCheckBox("L2TP ALG")
        w["ipsec"] = QCheckBox("IPSec ALG")
        w["sip"]   = QCheckBox("SIP ALG")
        w["ftp"]   = QCheckBox("FTP ALG")
        w["upnp"]  = QCheckBox("UPnP")
        for x in (w["l2tp"], w["ipsec"], w["sip"], w["ftp"], w["upnp"]):
            v.addWidget(x)
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._set_apply_alg_upnp)
        bb = QHBoxLayout(); bb.addStretch(); bb.addWidget(b); v.addLayout(bb)
        return card

    def _set_card_acs(self):
        card, v = self._adv_card(i18n.s("TR-069 / ACS"), color="#5D4037")
        w = self._set_w
        w["acs_en"]   = QCheckBox(i18n.s("Enable CWMP / TR-069"))
        w["acs_url"]  = QLineEdit(); w["acs_url"].setReadOnly(True)
        w["acs_user"] = QLineEdit(); w["acs_user"].setReadOnly(True)
        w["acs_int"]  = QLineEdit(); w["acs_int"].setReadOnly(True); w["acs_int"].setMinimumWidth(80)
        v.addWidget(w["acs_en"])
        v.addLayout(self._adv_row(i18n.s("URL"),      w["acs_url"]))
        v.addLayout(self._adv_row(i18n.s("Username"), w["acs_user"]))
        v.addLayout(self._adv_row(i18n.s("Inform Interval"), w["acs_int"]))
        b = QPushButton(i18n.s("Apply")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._set_apply_acs)
        bb = QHBoxLayout(); bb.addStretch(); bb.addWidget(b); v.addLayout(bb)
        return card

    def _set_card_account(self):
        card, v = self._adv_card(i18n.s("Admin Password"), color="#455A64")
        w = self._set_w
        w["pwd_old"] = QLineEdit(); w["pwd_old"].setEchoMode(QLineEdit.Password)
        w["pwd_new"] = QLineEdit(); w["pwd_new"].setEchoMode(QLineEdit.Password)
        w["pwd_new2"] = QLineEdit(); w["pwd_new2"].setEchoMode(QLineEdit.Password)
        v.addLayout(self._adv_row(i18n.s("Current Pwd"), w["pwd_old"]))
        v.addLayout(self._adv_row(i18n.s("New Pwd"),     w["pwd_new"]))
        v.addLayout(self._adv_row(i18n.s("Confirm"),     w["pwd_new2"]))
        b = QPushButton(i18n.s("Change Password")); b.setStyleSheet(self._adv_btn_style(True))
        b.clicked.connect(self._set_apply_password)
        bb = QHBoxLayout(); bb.addStretch(); bb.addWidget(b); v.addLayout(bb)
        return card

    def _set_card_system(self):
        card, v = self._adv_card(i18n.s("System Actions"), color="#BF360C")
        row = QHBoxLayout(); row.setSpacing(12)
        rb = QPushButton(i18n.s("Reboot Router")); rb.setStyleSheet(self._adv_btn_style(True))
        rb.clicked.connect(self._set_action_reboot)
        fr = QPushButton(i18n.s("Factory Reset"))
        fr.setStyleSheet(
            f"QPushButton {{ background:{theme_mod.t('err')}; color:#FFFFFF; border:none; "
             "border-radius:4px; padding:8px 18px; font-weight:bold; font-size:12px; }}"
            f"QPushButton:hover {{ background:{theme_mod.t('warn')}; }}")
        fr.clicked.connect(self._set_action_factory)
        # Open log folder — surface debug logs to the user so they can attach
        # them to bug reports without us having to walk them through paths.
        ol = QPushButton("📋  " + i18n.s("Open Logs Folder"))
        ol.setStyleSheet(self._adv_btn_style())
        ol.clicked.connect(self._set_open_logs)
        row.addWidget(rb); row.addWidget(fr); row.addWidget(ol); row.addStretch()
        v.addLayout(row)
        warn = QLabel(i18n.s("Sys warn"))
        warn.setStyleSheet(
            f"color:{theme_mod.t('fg_mute')}; font-size:11px; background:transparent;")
        v.addWidget(warn)
        return card

    def _set_open_logs(self):
        debug_log.info("user opened log folder", "ui")
        debug_log.open_log_folder()

    # ── Settings refresh + apply ──
    def _settings_refresh(self):
        """Fetch every settings group OFF the GUI thread.
        Seven sequential router calls were freezing the window for 5-15s
        on slow / virtualised LANs — pushing them to a worker thread keeps
        the UI responsive and lets us show a 'Loading…' chip in the status."""
        # Avoid stacking workers if the user clicks Refresh repeatedly.
        existing = getattr(self, "_settings_worker", None)
        if existing is not None and existing.isRunning():
            return

        self._set_status.setText(i18n.s("Loading…"))
        self._set_status.setStyleSheet(
            f"color:{theme_mod.t('warn')}; font-size:11px; "
            "background:transparent; font-weight:bold;")

        from PyQt5.QtCore import QThread, pyqtSignal as _Sig
        cl = self.hub.client

        class _Worker(QThread):
            result = _Sig(dict)
            def run(self):
                try:
                    self.result.emit({
                        "lan":   rapi.get_lan(cl) or {},
                        "fw":    rapi.get_firewall(cl) or {},
                        "alg":   rapi.get_alg(cl) or {},
                        "upnp":  rapi.get_upnp(cl) or {},
                        "acs":   rapi.get_tr069(cl) or {},
                        "ssids": rapi.get_wifi_ssids(cl) or [],
                        "aps":   rapi.get_wifi_aps(cl) or [],
                    })
                except Exception as e:
                    self.result.emit({"_error": str(e)})

        self._settings_worker = _Worker()
        self._settings_worker.result.connect(self._settings_apply_data)
        self._settings_worker.start()

    def _settings_apply_data(self, d):
        if "_error" in d:
            self._set_status.setText(f"Load failed: {d['_error'][:60]}")
            self._set_status.setStyleSheet(
                f"color:{theme_mod.t('err')}; font-size:11px; "
                "background:transparent;")
            debug_log.error(f"settings refresh failed: {d['_error']}", "settings")
            return
        try:
            lan   = d.get("lan",  {}) or {}
            fw    = d.get("fw",   {}) or {}
            alg   = d.get("alg",  {}) or {}
            up    = d.get("upnp", {}) or {}
            acs   = d.get("acs",  {}) or {}
            ssids = d.get("ssids", []) or []
            aps   = d.get("aps",   []) or []
            w = self._set_w
            # LAN
            w["ip"].setText(str(lan.get("IPInterfaceIPAddress","")))
            w["mask"].setText(str(lan.get("IPInterfaceSubnetMask","")))
            w["dhcp"].setChecked(str(lan.get("DHCPServerEnable")) == "1")
            w["dmin"].setText(str(lan.get("MinAddress","")))
            w["dmax"].setText(str(lan.get("MaxAddress","")))
            try: w["lease"].setValue(int(lan.get("DHCPLeaseTime") or 86400))
            except Exception: pass
            # WiFi
            def _ssid(i):
                return next((s for s in ssids if s.get("child_node_idx") == i), {})
            s1 = _ssid(1); s2 = _ssid(2)
            w["s1_en"].setChecked(str(s1.get("Enable")) == "1")
            w["s1_name"].setText(str(s1.get("SSID","")))
            w["s2_en"].setChecked(str(s2.get("Enable")) == "1")
            w["s2_name"].setText(str(s2.get("SSID","")))
            # leave passwords blank — user types only to change
            # Firewall
            w["fw_lvl"].setCurrentIndex(w["fw_lvl"].findData(str(fw.get("Firewall_Level") or "2")))
            # ALG + UPnP
            w["l2tp"].setChecked(str(alg.get("L2TPEnable")) == "1")
            w["ipsec"].setChecked(str(alg.get("IPSECEnable")) == "1")
            w["sip"].setChecked(str(alg.get("SIPEnable")) == "1")
            w["ftp"].setChecked(str(alg.get("FTPEnable")) == "1")
            w["upnp"].setChecked(str(up.get("Enable")) == "1")
            # ACS
            w["acs_en"].setChecked(str(acs.get("EnableCWMP")) == "1")
            w["acs_url"].setText(str(acs.get("URL","")))
            w["acs_user"].setText(str(acs.get("Username","")))
            w["acs_int"].setText(str(acs.get("PeriodicInformInterval","")))
            import time
            self._set_status.setText(f"Loaded · {time.strftime('%H:%M:%S')}")
            self._set_status.setStyleSheet("color:#2E7D32; font-size:11px;")
        except Exception as e:
            self._set_status.setText(f"Load failed: {str(e)[:60]}")
            self._set_status.setStyleSheet("color:#C62828; font-size:11px;")

    def _set_toast(self, ok, msg=""):
        self._set_status.setText(("✓ " if ok else "✗ ") + (msg or ""))
        self._set_status.setStyleSheet(
            f"color:{'#2E7D32' if ok else '#C62828'}; font-size:11px; font-weight:bold;")
        QTimer.singleShot(2400, self._settings_refresh)

    def _set_apply_lan(self):
        try:
            w = self._set_w
            rapi.set_lan(self.hub.client,
                ip=w["ip"].text().strip() or None,
                mask=w["mask"].text().strip() or None,
                dhcp_enable=w["dhcp"].isChecked(),
                dhcp_min=w["dmin"].text().strip() or None,
                dhcp_max=w["dmax"].text().strip() or None,
                lease_sec=w["lease"].value())
            self._set_toast(True, "LAN applied (router may take ~10s to apply)")
        except Exception as e: self._set_toast(False, str(e)[:60])

    def _set_apply_wifi(self):
        try:
            w = self._set_w
            for idx, en, nm, pw in ((1, w["s1_en"], w["s1_name"], w["s1_pwd"]),
                                      (2, w["s2_en"], w["s2_name"], w["s2_pwd"])):
                rapi.set_wifi_ssid(self.hub.client, idx,
                    ssid_name=nm.text().strip(),
                    password=(pw.text() if pw.text() else None),
                    enable=en.isChecked())
            self._set_toast(True, "Wi-Fi SSIDs applied")
        except Exception as e: self._set_toast(False, str(e)[:60])

    def _set_apply_firewall(self):
        try:
            rapi.set_firewall_level(self.hub.client,
                int(self._set_w["fw_lvl"].currentData() or "2"))
            self._set_toast(True, "Firewall level applied")
        except Exception as e: self._set_toast(False, str(e)[:60])

    def _set_apply_alg_upnp(self):
        try:
            w = self._set_w
            rapi.set_alg(self.hub.client,
                l2tp=w["l2tp"].isChecked(), ipsec=w["ipsec"].isChecked(),
                sip=w["sip"].isChecked(), ftp=w["ftp"].isChecked())
            rapi.set_upnp(self.hub.client, w["upnp"].isChecked())
            self._set_toast(True, "ALG / UPnP applied")
        except Exception as e: self._set_toast(False, str(e)[:60])

    def _set_apply_acs(self):
        try:
            rapi.set_tr069_enable(self.hub.client, self._set_w["acs_en"].isChecked())
            self._set_toast(True, "TR-069 enable applied")
        except Exception as e: self._set_toast(False, str(e)[:60])

    def _set_apply_password(self):
        try:
            w = self._set_w
            old, new, new2 = w["pwd_old"].text(), w["pwd_new"].text(), w["pwd_new2"].text()
            if not old or not new:
                self._set_toast(False, "Fill current and new password"); return
            if new != new2:
                self._set_toast(False, "New passwords don't match"); return
            r = rapi.change_admin_password(self.hub.client, old, new)
            ok = isinstance(r, dict) and r.get("retcode", r.get("RetCode", "0")) in ("0", 0)
            self._set_toast(ok, "Password changed" if ok else f"Failed: {r}")
            if ok:
                w["pwd_old"].clear(); w["pwd_new"].clear(); w["pwd_new2"].clear()
        except Exception as e: self._set_toast(False, str(e)[:60])

    def _set_action_reboot(self):
        if QMessageBox.question(self, "Reboot Router",
                                  "Reboot the router now? Connection will drop for ~60s.",
                                  QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            rapi.reboot_device(self.hub.client)
            self._set_toast(True, "Reboot command sent")
        except Exception as e: self._set_toast(False, str(e)[:60])

    def _set_action_factory(self):
        if QMessageBox.warning(self, "Factory Reset",
                                "ALL settings will be erased. Continue?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            rapi.factory_reset(self.hub.client)
            self._set_toast(True, "Factory reset triggered")
        except Exception as e: self._set_toast(False, str(e)[:60])


    # ────────────────────── IP Scan page ──────────────────────
    def _build_ipscan_page(self):
        """IP monitor + Cloudflare speed test + airplane-mode IP-changer.
        Spawns its own background workers; they're started/stopped from
        _ipscan_start_monitor / _ipscan_stop_all so a hidden tab doesn't
        keep hammering the public-IP endpoints."""
        from PyQt5.QtWidgets import QTextEdit, QDialog, QSizePolicy
        t = theme_mod.t

        # Worker state — kept on self so view-rebuilds (theme/lang change)
        # can stop them cleanly before we drop the widgets.
        self._ipscan_log_html      = []
        self._ipscan_speed_history = []
        self._ipscan_w             = {}
        self._ipscan_state         = {
            "auto_speed":     False,
            "pinning":        False,
            "pinning_count":  0,
            "test_running":   False,
            "change_running": False,
            "last_pub":       "",
        }
        self._ipscan_monitor   = None
        self._ipscan_changer   = None
        self._ipscan_speed_th  = None

        page = QWidget()
        page.setStyleSheet(f"QWidget {{ background:{t('bg')}; }}")
        lay = QVBoxLayout(page); lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)

        # Hero
        lay.addWidget(self._adv_hero(i18n.s("IP Tools"), i18n.s("IP sub")))

        # Status row
        status_card, sv = self._adv_card(i18n.s("Current Network"), color=t("accent"))
        sg = QGridLayout(); sg.setHorizontalSpacing(20); sg.setVerticalSpacing(6)
        # 3 columns: status / wan / public
        def _make_chip(initial="—"):
            l = QLabel(initial)
            f = QFont("Consolas", 13); f.setBold(True); l.setFont(f)
            l.setStyleSheet(
                f"color:{t('fg')}; padding:8px 14px; "
                f"background:{t('card_alt')}; border:1px solid {t('border')}; "
                "border-radius:6px; min-width:160px;")
            l.setAlignment(Qt.AlignCenter)
            return l

        for col, (key, fid) in enumerate([("Status","status"),
                                            ("WAN IP","wan"),
                                            ("Public IP","pub")]):
            cap = QLabel(i18n.s(key))
            cap.setStyleSheet(f"color:{t('fg_dim')}; font-size:11px; font-weight:bold; "
                                "letter-spacing:1px; background:transparent;")
            cap.setAlignment(Qt.AlignCenter)
            sg.addWidget(cap, 0, col)
            chip = _make_chip()
            self._ipscan_w[fid] = chip
            sg.addWidget(chip, 1, col)
            sg.setColumnStretch(col, 1)
        sv.addLayout(sg)

        self._ipscan_w["proc"] = QLabel("")
        self._ipscan_w["proc"].setAlignment(Qt.AlignCenter)
        self._ipscan_w["proc"].setStyleSheet(
            f"color:{t('warn')}; font-weight:bold; padding:6px; "
            "background:transparent;")
        self._ipscan_w["proc"].setVisible(False)
        sv.addWidget(self._ipscan_w["proc"])
        lay.addWidget(status_card)

        # Quick Actions row
        actions_card, av = self._adv_card(i18n.s("Quick Actions"), color=t("ok"))
        ar = QHBoxLayout(); ar.setSpacing(10)
        self._ipscan_w["btn_change"] = self._make_action_btn(
            i18n.s("Change IP"), t("accent"), "#FFFFFF", t("accent"), primary=True)
        self._ipscan_w["btn_change"].clicked.connect(self._ipscan_change_ip)
        self._ipscan_w["btn_speed"]  = self._make_action_btn(
            i18n.s("Speed Test"), t("ok"), "#FFFFFF", t("ok"), primary=True)
        self._ipscan_w["btn_speed"].clicked.connect(self._ipscan_run_speed)
        self._ipscan_w["btn_stats"]  = self._make_action_btn(
            i18n.s("Speed Stats"), t("card"), t("fg"), t("border"))
        self._ipscan_w["btn_stats"].clicked.connect(self._ipscan_show_stats)
        self._ipscan_w["btn_stop"]   = self._make_action_btn(
            i18n.s("Stop"), t("err"), "#FFFFFF", t("err"))
        self._ipscan_w["btn_stop"].clicked.connect(self._ipscan_stop_auto)
        for b in (self._ipscan_w["btn_change"], self._ipscan_w["btn_speed"],
                   self._ipscan_w["btn_stats"], self._ipscan_w["btn_stop"]):
            ar.addWidget(b)
        ar.addStretch()
        av.addLayout(ar)
        lay.addWidget(actions_card)

        # Auto + IP Pinning card
        adv_card, dv = self._adv_card(i18n.s("IP Pinning"), color=t("warn"))
        # Auto speed checkbox row
        self._ipscan_w["auto"] = QCheckBox(i18n.s("Auto Speed Test"))
        self._ipscan_w["auto"].toggled.connect(self._ipscan_toggle_auto)
        dv.addWidget(self._ipscan_w["auto"])

        desc = QLabel(i18n.s("IP Pin desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color:{t('fg_mute')}; font-size:11px; background:transparent;")
        dv.addWidget(desc)

        pin_row = QHBoxLayout(); pin_row.setSpacing(10)
        self._ipscan_w["target_wan"] = QLineEdit()
        self._ipscan_w["target_wan"].setPlaceholderText("WAN: 10.193.89")
        self._ipscan_w["target_pub"] = QLineEdit()
        self._ipscan_w["target_pub"].setPlaceholderText("Public: 51.253.184")
        pin_row.addLayout(self._adv_row(i18n.s("Target WAN"),    self._ipscan_w["target_wan"]))
        pin_row.addLayout(self._adv_row(i18n.s("Target Public"), self._ipscan_w["target_pub"]))
        dv.addLayout(pin_row)

        pin_actions = QHBoxLayout()
        self._ipscan_w["btn_pin"] = QPushButton(i18n.s("Start Pinning"))
        self._ipscan_w["btn_pin"].setStyleSheet(self._adv_btn_style(True))
        self._ipscan_w["btn_pin"].clicked.connect(self._ipscan_start_pinning)
        self._ipscan_w["pin_count"] = QLabel("")
        self._ipscan_w["pin_count"].setStyleSheet(
            f"color:{t('warn')}; font-weight:bold; background:transparent;")
        pin_actions.addWidget(self._ipscan_w["pin_count"])
        pin_actions.addStretch()
        pin_actions.addWidget(self._ipscan_w["btn_pin"])
        dv.addLayout(pin_actions)
        lay.addWidget(adv_card)

        # Network log card
        log_card, lv = self._adv_card(i18n.s("Network Log"), color=t("accent_2"))
        log_actions = QHBoxLayout()
        log_actions.addStretch()
        clear_btn = QPushButton(i18n.s("Clear Log"))
        clear_btn.setStyleSheet(self._adv_btn_style())
        clear_btn.clicked.connect(self._ipscan_clear_log)
        save_btn  = QPushButton(i18n.s("Save Log"))
        save_btn.setStyleSheet(self._adv_btn_style())
        save_btn.clicked.connect(self._ipscan_save_log)
        log_actions.addWidget(clear_btn); log_actions.addWidget(save_btn)
        lv.addLayout(log_actions)

        self._ipscan_w["log"] = QTextEdit()
        self._ipscan_w["log"].setReadOnly(True)
        self._ipscan_w["log"].setMinimumHeight(250)
        self._ipscan_w["log"].setStyleSheet(
            f"QTextEdit {{ background:{t('card_alt')}; color:{t('fg')}; "
            f"border:1px solid {t('border_lt')}; border-radius:6px; "
            "font-family:Consolas; font-size:11px; padding:8px; }}")
        self._ipscan_log_render()
        lv.addWidget(self._ipscan_w["log"])
        lay.addWidget(log_card)
        return page

    # ── IP Scan: lifecycle helpers ──
    def _ipscan_start_monitor(self):
        """Idempotent: only starts the monitor thread if it isn't already alive."""
        from shared.ip_workers import IpMonitorWorker
        mon = getattr(self, "_ipscan_monitor", None)
        if mon and mon.isRunning(): return
        self._ipscan_monitor = IpMonitorWorker(self.hub.client, interval_ms=2500)
        self._ipscan_monitor.update.connect(self._ipscan_on_monitor)
        self._ipscan_monitor.start()

    def _ipscan_stop_all(self):
        """Stops every IP-scan worker. Called on logout, theme/lang switch,
        and view-stack rebuild — anywhere the underlying widgets vanish.
        Handles both QThread workers (have isRunning/quit/wait) and the
        QObject-based FastSpeedTest (only has stop)."""
        for attr in ("_ipscan_monitor", "_ipscan_changer", "_ipscan_speed_th"):
            w = getattr(self, attr, None)
            if w is None: continue
            try:
                if hasattr(w, "stop"): w.stop()
            except Exception: pass
            try:
                if hasattr(w, "isRunning") and w.isRunning():
                    w.quit(); w.wait(500)
            except Exception: pass
            setattr(self, attr, None)
        if hasattr(self, "_ipscan_state"):
            self._ipscan_state["change_running"] = False
            self._ipscan_state["test_running"]   = False

    # ── IP Scan: monitor signal handlers ──
    def _ipscan_on_monitor(self, d):
        t = theme_mod.t
        st = d.get("status", "Unknown")
        wan = d.get("wan_ip", "—") or "—"
        pub = d.get("public_ip", "—") or "—"

        # Color status by state
        chip = self._ipscan_w["status"]
        if st == "Connected":
            chip.setText("● " + i18n.s("Connected"))
            chip.setStyleSheet(
                f"color:#FFFFFF; padding:8px 14px; background:{t('ok')}; "
                f"border:1px solid {t('ok')}; border-radius:6px; font-weight:bold;")
        elif st == "Disconnected":
            chip.setText("✈ " + i18n.s("Disconnected"))
            chip.setStyleSheet(
                f"color:#FFFFFF; padding:8px 14px; background:{t('err')}; "
                f"border:1px solid {t('err')}; border-radius:6px; font-weight:bold;")
        else:
            chip.setText("⟳ " + i18n.s("Connecting..."))
            chip.setStyleSheet(
                f"color:#FFFFFF; padding:8px 14px; background:{t('warn')}; "
                f"border:1px solid {t('warn')}; border-radius:6px; font-weight:bold;")
        self._ipscan_w["wan"].setText(wan)
        self._ipscan_w["pub"].setText(pub)

        # Emit a log entry only when something actually changed
        prev = self._ipscan_state.get("last_snapshot")
        cur  = (st, wan, pub)
        if prev != cur:
            self._ipscan_state["last_snapshot"] = cur
            self._ipscan_log_status(st, wan, pub)

            # IP pinning logic
            from shared.ip_workers import ip_matches
            if self._ipscan_state["pinning"] and st == "Connected" \
                    and not self._ipscan_state["change_running"]:
                tw = self._ipscan_w["target_wan"].text().strip()
                tp = self._ipscan_w["target_pub"].text().strip()
                wan_match = ip_matches(wan, tw) if tw else False
                pub_match = ip_matches(pub, tp) if tp else False
                # If both targets specified, both must match. Else the one set wins.
                hit = (wan_match and pub_match) if (tw and tp) else (wan_match or pub_match)
                if hit:
                    self._ipscan_state["pinning"] = False
                    self._ipscan_w["pin_count"].setText("")
                    self._ipscan_log_html.insert(0,
                        f'<div style="color:{t("ok")}; background:{t("ok_bg")}; '
                        f'padding:8px; border-radius:4px; font-weight:bold;">'
                        f'🎯 {i18n.s("IP found")} '
                        f'({self._ipscan_state["pinning_count"]} '
                        f'{i18n.s("Pinning attempts")})</div>')
                    self._ipscan_log_render()
                    return
                # No match — keep cycling
                self._ipscan_state["pinning_count"] += 1
                self._ipscan_w["pin_count"].setText(
                    f"({self._ipscan_state['pinning_count']} "
                    f"{i18n.s('Pinning attempts')})")
                QTimer.singleShot(2500, self._ipscan_change_ip_if_pinning)

            # Auto speed test on new public IP
            if self._ipscan_state["auto_speed"] and st == "Connected" \
                    and pub and pub not in ("—", "Failed!", "") \
                    and pub != self._ipscan_state["last_pub"] \
                    and not self._ipscan_state["test_running"]:
                self._ipscan_state["last_pub"] = pub
                QTimer.singleShot(2500, self._ipscan_run_speed)

    def _ipscan_change_ip_if_pinning(self):
        """Helper guard — pinning may have been cancelled in the gap."""
        if self._ipscan_state["pinning"] and not self._ipscan_state["change_running"]:
            self._ipscan_change_ip()

    # ── IP Scan: log helpers ──
    def _ipscan_log_status(self, status, wan, pub, speed_data=None):
        import time as _t
        t = theme_mod.t
        when   = _t.strftime("%H:%M:%S")
        st_col = t("ok") if status == "Connected" else t("err") \
                  if status == "Disconnected" else t("warn")
        line = (f'<div style="background:{t("card")}; padding:8px 10px; '
                f'border-radius:4px; margin-bottom:6px; '
                f'border-left:3px solid {st_col};">'
                f'<span style="color:{t("warn")}; font-weight:bold;">{when}</span> · '
                f'<b>{i18n.s("Status")}:</b> '
                f'<span style="color:{st_col}; font-weight:bold;">{status}</span> · '
                f'<b>{i18n.s("WAN IP")}:</b> '
                f'<span style="color:{t("accent")};">{wan}</span> · '
                f'<b>{i18n.s("Public IP")}:</b> '
                f'<span style="color:{t("warn")};">{pub}</span>')
        if speed_data:
            line += (f' · <b>{i18n.s("Speed")}:</b> '
                     f'<span style="color:{t("ok")};">{speed_data["download"]} Mbps</span>'
                     f' · <b>{i18n.s("Ping")}:</b> '
                     f'<span style="color:{t("warn")};">{speed_data["ping"]} ms</span>'
                     f' · <b>{i18n.s("Upload")}:</b> '
                     f'<span style="color:{t("accent_2")};">{speed_data["upload"]} Mbps</span>')
        line += "</div>"
        self._ipscan_log_html.insert(0, line)
        # Keep history bounded — 200 entries is plenty for the human, more
        # would just slow the QTextEdit refresh.
        if len(self._ipscan_log_html) > 200:
            self._ipscan_log_html = self._ipscan_log_html[:200]
        self._ipscan_log_render()

    def _ipscan_log_render(self):
        if "log" not in self._ipscan_w: return
        body = "".join(self._ipscan_log_html) if self._ipscan_log_html \
                else f'<div style="color:{theme_mod.t("fg_mute")}; text-align:center; padding:20px;">{i18n.s("No logs")}</div>'
        self._ipscan_w["log"].setHtml(body)

    def _ipscan_clear_log(self):
        self._ipscan_log_html = []
        self._ipscan_speed_history = []
        self._ipscan_log_render()

    def _ipscan_save_log(self):
        from PyQt5.QtWidgets import QFileDialog
        import time as _t, re
        default = f"IP_Scan_Log_{_t.strftime('%Y%m%d_%H%M%S')}.txt"
        path, _f = QFileDialog.getSaveFileName(self, i18n.s("Save Log"),
                                                  default, "Text (*.txt)")
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{i18n.s('IP Tools')} — {i18n.s('Network Log')}\n")
                f.write(f"Generated: {_t.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                # Strip HTML for plain-text dump
                strip = re.compile(r"<[^>]+>")
                for entry in self._ipscan_log_html:
                    f.write(strip.sub("", entry).strip() + "\n\n")
        except Exception as e:
            QMessageBox.warning(self, "Save failed", str(e))

    def _ipscan_set_proc(self, msg, ok=False):
        t = theme_mod.t
        if not msg:
            self._ipscan_w["proc"].setVisible(False); return
        self._ipscan_w["proc"].setText(msg)
        self._ipscan_w["proc"].setStyleSheet(
            f"color:{t('ok') if ok else t('warn')}; font-weight:bold; "
             "padding:6px; background:transparent;")
        self._ipscan_w["proc"].setVisible(True)

    # ── IP Scan: action handlers ──
    def _ipscan_change_ip(self):
        from shared.ip_workers import IpChangeWorker
        if self._ipscan_state["change_running"]:
            return
        debug_log.info("IP change requested", "ipscan")
        self._ipscan_state["change_running"] = True
        t = theme_mod.t
        self._ipscan_log_html.insert(0,
            f'<div style="color:{t("accent")}; background:{t("accent_bg")}; '
            f'padding:8px; border-radius:4px; font-weight:bold;">🔄 Starting IP change…</div>')
        self._ipscan_log_render()

        w = IpChangeWorker(self.hub.client)
        w.progress.connect(lambda m: self._ipscan_set_proc(m))
        w.done.connect(self._ipscan_on_change_done)
        self._ipscan_changer = w
        w.start()

    def _ipscan_on_change_done(self, ok, msg):
        t = theme_mod.t
        col = t("ok") if ok else t("err")
        bg  = t("ok_bg") if ok else t("err_bg")
        self._ipscan_log_html.insert(0,
            f'<div style="color:{col}; background:{bg}; padding:8px; '
            f'border-radius:4px; font-weight:bold;">'
            f'{"✅" if ok else "❌"} {msg}</div>')
        self._ipscan_log_render()
        self._ipscan_set_proc("")
        self._ipscan_state["change_running"] = False

    def _ipscan_run_speed(self):
        """Drive a hidden fast.com page off-screen and scrape its results.
        Fast.com's numbers track Netflix's nearest OCA, which matches what
        the user actually feels — Cloudflare can underread by 3-5× on some
        carrier peering arrangements."""
        if self._ipscan_state["test_running"]: return

        # Import + construction wrapped — a missing PyQtWebEngine, a
        # broken Qt resource bundle, or a denied GPU process all surface
        # here, and we'd rather log them than have the user see a sudden
        # window close.
        try:
            from shared.fast_speed_test import FastSpeedTest
        except Exception as e:
            self._ipscan_log_html.insert(0,
                f'<div style="color:{theme_mod.t("err")};">'
                f'⚠️ Speed test unavailable (PyQtWebEngine missing): {e}</div>')
            self._ipscan_log_render()
            return

        # Tear down any previous runner before starting a fresh one.
        prev = getattr(self, "_ipscan_speed_th", None)
        if prev is not None:
            try: prev.stop()
            except Exception: pass

        try:
            runner = FastSpeedTest(parent=self, timeout_sec=120)
        except Exception as e:
            self._ipscan_log_html.insert(0,
                f'<div style="color:{theme_mod.t("err")};">'
                f'⚠️ Cannot create speed test runner: {e}</div>')
            self._ipscan_log_render()
            return

        self._ipscan_state["test_running"] = True
        self._ipscan_set_proc("⚡ Opening Fast.com (hidden)…")
        debug_log.info("speed test started (Fast.com)", "ipscan")
        runner.progress.connect(lambda m: self._ipscan_set_proc(f"⚡ {m}"))
        runner.done.connect(self._ipscan_on_speed_done)
        self._ipscan_speed_th = runner
        try:
            runner.start()
        except Exception as e:
            self._ipscan_state["test_running"] = False
            self._ipscan_set_proc("")
            self._ipscan_log_html.insert(0,
                f'<div style="color:{theme_mod.t("err")};">'
                f'⚠️ Failed to launch fast.com: {e}</div>')
            self._ipscan_log_render()

    def _ipscan_on_speed_done(self, result):
        self._ipscan_state["test_running"] = False
        self._ipscan_set_proc("")
        debug_log.info(f"speed test done: {result}", "ipscan")
        if "error" in result:
            t = theme_mod.t
            self._ipscan_log_html.insert(0,
                f'<div style="color:{t("err")};">⚠️ Speed test failed: {result["error"]}</div>')
            self._ipscan_log_render()
            return
        # Log the speed result on top of the latest snapshot (status/IPs from monitor)
        st  = self._ipscan_state.get("last_snapshot", ("Connected","Unknown","Unknown"))
        self._ipscan_log_status("Connected", st[1], st[2], speed_data=result)
        self._ipscan_speed_history.append({
            "wan": st[1], "pub": st[2],
            "download": result["download"],
            "upload":   result["upload"],
            "ping":     result["ping"],
        })

    def _ipscan_toggle_auto(self, on):
        self._ipscan_state["auto_speed"] = bool(on)

    def _ipscan_stop_auto(self):
        self._ipscan_state["auto_speed"]    = False
        self._ipscan_state["pinning"]       = False
        if "auto" in self._ipscan_w:
            self._ipscan_w["auto"].setChecked(False)
        self._ipscan_w["pin_count"].setText("")
        self._ipscan_set_proc("")

    def _ipscan_start_pinning(self):
        tw = self._ipscan_w["target_wan"].text().strip()
        tp = self._ipscan_w["target_pub"].text().strip()
        if not tw and not tp:
            QMessageBox.information(self, i18n.s("IP Pinning"),
                "Enter a WAN or Public IP pattern first.")
            return
        self._ipscan_state["pinning"]       = True
        self._ipscan_state["pinning_count"] = 0
        self._ipscan_state["auto_speed"]    = False
        self._ipscan_w["auto"].setChecked(False)
        t = theme_mod.t
        self._ipscan_log_html.insert(0,
            f'<div style="color:{t("warn")}; background:{t("warn_bg")}; '
            f'padding:8px; border-radius:4px; font-weight:bold;">'
            f'🔍 {i18n.s("Searching IP")}</div>')
        self._ipscan_log_render()
        self._ipscan_change_ip()

    def _ipscan_show_stats(self):
        """Modal sortable table of every captured speed test result."""
        from PyQt5.QtWidgets import QDialog, QHeaderView as _HV
        if not self._ipscan_speed_history:
            QMessageBox.information(self, i18n.s("Speed Stats"),
                                      i18n.s("No logs"))
            return
        t = theme_mod.t
        dlg = QDialog(self); dlg.setWindowTitle(i18n.s("Speed Stats"))
        dlg.setMinimumSize(720, 480)
        dlg.setStyleSheet(f"QDialog {{ background:{t('bg')}; }}")
        v = QVBoxLayout(dlg); v.setContentsMargins(20, 16, 20, 16); v.setSpacing(12)
        hdr = QLabel(f"{i18n.s('Speed Stats')} · "
                      f"{i18n.s('Test count')}: {len(self._ipscan_speed_history)}")
        hdr.setStyleSheet(f"color:{t('accent')}; font-size:16px; font-weight:bold; "
                            "background:transparent;")
        v.addWidget(hdr)

        tbl = QTableWidget(len(self._ipscan_speed_history), 6)
        tbl.setHorizontalHeaderLabels(["#",
                                         i18n.s("WAN IP"),
                                         i18n.s("Public IP"),
                                         i18n.s("Speed"),
                                         i18n.s("Upload"),
                                         i18n.s("Ping")])
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSortingEnabled(True)
        tbl.horizontalHeader().setSectionResizeMode(_HV.Stretch)
        tbl.verticalHeader().setVisible(False)
        # Sort numerically: store the raw float in UserRole, table sort uses it.
        from PyQt5.QtCore import Qt as _Qt
        for i, row in enumerate(self._ipscan_speed_history):
            cells = [str(i + 1), row["wan"], row["pub"],
                      f"{row['download']:.2f} Mbps",
                      f"{row['upload']:.2f} Mbps",
                      f"{row['ping']:.1f} ms"]
            sort_keys = [i + 1, row["wan"], row["pub"],
                          row["download"], row["upload"], row["ping"]]
            for c, val in enumerate(cells):
                it = QTableWidgetItem(val)
                it.setData(_Qt.UserRole, sort_keys[c])
                it.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(i, c, it)
        v.addWidget(tbl, 1)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(self._adv_btn_style(True))
        close_btn.clicked.connect(dlg.accept)
        bb = QHBoxLayout(); bb.addStretch(); bb.addWidget(close_btn); v.addLayout(bb)
        dlg.exec_()


    # ────────────────────── AT Command page ──────────────────────
    def _build_atcmd_page(self):
        """Raw-AT console wired to the modem via api_client.send_at().
        Exposes a Send button + a quick-presets bar for the commands users
        ask for most (signal, IMEI, manufacturer, serving cell)."""
        from PyQt5.QtWidgets import QTextEdit
        t = theme_mod.t

        page = QWidget()
        page.setStyleSheet(f"QWidget {{ background:{t('bg')}; }}")
        # No scroll — content fits via compact card layout.
        lay = QVBoxLayout(page); lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)

        lay.addWidget(self._adv_hero(i18n.s("AT title"), i18n.s("AT sub")))

        self._at_w = {}

        # Command input row
        cmd_card, cv = self._adv_card(i18n.s("Command"), color=t("accent"))
        self._at_w["input"] = QLineEdit()
        self._at_w["input"].setPlaceholderText(i18n.s("AT placeholder"))
        # Submit on Enter for convenience
        self._at_w["input"].returnPressed.connect(self._at_send)
        cv.addWidget(self._at_w["input"])

        bar = QHBoxLayout()
        send_btn = QPushButton("📡  " + i18n.s("Send"))
        send_btn.setStyleSheet(self._adv_btn_style(True))
        send_btn.clicked.connect(self._at_send)
        clear_btn = QPushButton(i18n.s("Clear"))
        clear_btn.setStyleSheet(self._adv_btn_style())
        clear_btn.clicked.connect(self._at_clear)
        bar.addStretch(); bar.addWidget(clear_btn); bar.addWidget(send_btn)
        cv.addLayout(bar)
        lay.addWidget(cmd_card)

        # Quick presets
        presets_card, pv = self._adv_card(i18n.s("Quick commands"), color=t("ok"))
        # (label, AT command)
        presets = [
            ("ATI",                       "ATI"),
            ("Signal · AT+CSQ",           "AT+CSQ"),
            ("IMEI · AT+CGSN",            "AT+CGSN"),
            ("Firmware · AT+CGMR",        "AT+CGMR"),
            ("Manufacturer · AT+CGMI",    "AT+CGMI"),
            ("Model · AT+CGMM",           "AT+CGMM"),
            ("Operator · AT+COPS?",       "AT+COPS?"),
            ("Reg status · AT+CREG?",     "AT+CREG?"),
            ("EPS reg · AT+CEREG?",       "AT+CEREG?"),
            ("Serving cell · AT+QENG=\"servingcell\"",
                                          'AT+QENG="servingcell"'),
            ("Neighbor cell · AT+QENG=\"neighbourcell\"",
                                          'AT+QENG="neighbourcell"'),
        ]
        grid = QGridLayout(); grid.setSpacing(6)
        for i, (label, cmd) in enumerate(presets):
            b = QPushButton(label)
            b.setStyleSheet(self._adv_btn_style())
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=cmd: self._at_run_preset(c))
            grid.addWidget(b, i // 3, i % 3)
        pv.addLayout(grid)
        lay.addWidget(presets_card)

        # Response area
        resp_card, rv = self._adv_card(i18n.s("Response"), color=t("accent_2"))
        self._at_w["resp"] = QTextEdit()
        self._at_w["resp"].setReadOnly(True)
        self._at_w["resp"].setMinimumHeight(280)
        self._at_w["resp"].setStyleSheet(
            f"QTextEdit {{ background:{t('card_alt')}; color:{t('fg')}; "
            f"border:1px solid {t('border_lt')}; border-radius:6px; "
            "font-family:Consolas; font-size:12px; padding:10px; }}")
        rv.addWidget(self._at_w["resp"])
        lay.addWidget(resp_card, 1)
        return page

    def _at_send(self):
        cmd = self._at_w["input"].text().strip()
        if not cmd: return
        self._at_run_preset(cmd)

    def _at_run_preset(self, cmd: str):
        """Echoes the command, sends it through the websocket bridge, and
        prepends the response above any earlier output. We don't push
        send_at onto a worker thread because api_client._post_api is already
        blocking on the websocket — fine for a one-shot user click."""
        from PyQt5.QtWidgets import QApplication
        import time as _t
        t = theme_mod.t
        when = _t.strftime("%H:%M:%S")
        debug_log.info(f"AT command sent: {cmd}", "at")
        # Keep prior history — prepend the in-flight echo above it
        prior = self._at_w["resp"].toHtml() or ""
        self._at_w["resp"].setHtml(
            f'<div style="color:{t("accent")}; margin-top:6px; font-weight:bold;">'
            f'[{when}] » {cmd}</div>'
            f'<div style="color:{t("warn")};">{i18n.s("Sending")}…</div>'
            + prior)
        QApplication.processEvents()
        try:
            resp = self.hub.client.send_at(cmd)
            debug_log.info(f"AT response ({len(resp)} chars)", "at")
        except Exception as e:
            debug_log.exc(f"AT command failed: {cmd} → {e}", "at")
            resp = f"ERROR: {e}"
        # Prepend formatted response
        body = (resp or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        out = (f'<div style="color:{t("accent")}; margin-top:6px; font-weight:bold;">'
               f'[{when}] » {cmd}</div>'
               f'<pre style="color:{t("fg")}; background:{t("card")}; padding:8px 10px; '
               f'border-left:3px solid {t("ok")}; margin:0 0 8px 0; '
               f'white-space:pre-wrap; word-wrap:break-word;">{body}</pre>')
        self._at_w["resp"].setHtml(out + prior)

    def _at_clear(self):
        if "resp" in self._at_w:
            self._at_w["resp"].clear()


if __name__ == "__main__":
    run_design(EngWindow, "FiberGuard 1 - Engineering Console")
