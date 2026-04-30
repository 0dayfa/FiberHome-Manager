"""DataHub — central state manager. Gathers data from workers, emits unified dict."""
import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread

from api_client import RouterClient
from workers import (AuthWorker, HeaderWorker, RadioWorker, CAWorker,
                      SystemWorker, SimWorker, TrafficWorker,
                      DevicesWorker, WiFiWorker, LogWorker, MiscWorker)
import router_api as rapi
from shared import debug_log


class DataHub(QObject):
    """Single source of truth. Other widgets connect to .updated signal."""
    auth_status = pyqtSignal(bool, str)
    updated     = pyqtSignal(dict)
    log_lines   = pyqtSignal(object)

    def __init__(self, ip="192.168.8.1", user="superadmin", pwd="F1ber$dm", parent=None):
        super().__init__(parent)
        self.client = RouterClient(ip)
        self.user, self.pwd = user, pwd
        self.ip = ip
        self.state = {
            "radio": {}, "header": {}, "system": {}, "sim": {},
            "traffic": {}, "ca": {}, "devices": [], "wifi": {},
            "misc": {}, "_neighbors": [],
        }
        self._build_workers()
        self._wire()
        self._workers_started = False

    def _build_workers(self):
        c = self.client
        self.w_auth   = AuthWorker(c, self.user, self.pwd)
        self.w_header = HeaderWorker(c, 2000)   # was 4000 — faster
        self.w_radio  = RadioWorker(c, 1500)    # was 4000 — near-realtime
        self.w_ca     = CAWorker(c, 1500)       # was 8000 — match radio for real-time
        self.w_system = SystemWorker(c, 4000)   # was 10000 — for live CPU/RAM gauges
        self.w_sim    = SimWorker(c, 20000)
        self.w_traffic= TrafficWorker(c, 2000)  # was 5000 — live KB/s
        self.w_devices= DevicesWorker(c, 12000)
        self.w_wifi   = WiFiWorker(c, 30000)
        self.w_logs   = LogWorker(c, 20000)
        self.w_misc   = MiscWorker(c, 45000)

    def _wire(self):
        self.w_auth.status.connect(self._on_auth)
        self.w_header.data.connect(lambda d: self._update("header", d))
        self.w_radio.data.connect(self._on_radio)
        self.w_ca.data.connect(lambda d: self._update("ca", d))
        self.w_system.data.connect(lambda d: self._update("system", d))
        self.w_sim.data.connect(lambda d: self._update("sim", d))
        self.w_traffic.data.connect(lambda d: self._update("traffic", d))
        self.w_devices.data.connect(lambda d: self._update("devices", d))
        self.w_wifi.data.connect(lambda d: self._update("wifi", d))
        self.w_misc.data.connect(lambda d: self._update("misc", d))
        self.w_logs.new_lines.connect(lambda lns: self.log_lines.emit(lns))

    def _on_radio(self, d):
        if isinstance(d, dict):
            self.state["_neighbors"] = d.get("_neighbors", [])
        self._update("radio", d)

    def _update(self, key, d):
        self.state[key] = d
        self.updated.emit(self.state)

    def _on_auth(self, ok, msg):
        debug_log.info(f"auth callback: ok={ok}, msg={msg}", "auth")
        self.auth_status.emit(bool(ok), msg)
        if ok and not self._workers_started:
            self._workers_started = True
            self._launch_workers()

    def _launch_workers(self):
        debug_log.info("launching background workers (staggered)", "hub")
        QTimer.singleShot(200,  lambda: self._safe(self.w_header.start))
        QTimer.singleShot(1500, lambda: self._safe(self.w_radio.start))
        QTimer.singleShot(2800, lambda: self._safe(self.w_ca.start))
        QTimer.singleShot(4200, lambda: self._safe(self.w_system.start))
        QTimer.singleShot(5500, lambda: self._safe(self.w_sim.start))
        QTimer.singleShot(7000, lambda: self._safe(self.w_traffic.start))
        QTimer.singleShot(8500, lambda: self._safe(self.w_devices.start))
        QTimer.singleShot(10000,lambda: self._safe(self.w_wifi.start))
        QTimer.singleShot(12000,lambda: self._safe(self.w_logs.start))
        QTimer.singleShot(14000,lambda: self._safe(self.w_misc.start))

    def _safe(self, fn):
        try: fn()
        except Exception as e:
            debug_log.exc(f"worker start failed for {fn}: {e}", "hub")

    def start(self):
        debug_log.info(f"starting auth worker (user={self.user})", "hub")
        self.w_auth.start()

    def stop(self):
        debug_log.info("stopping all workers", "hub")
        for w in (self.w_auth, self.w_header, self.w_radio, self.w_ca,
                  self.w_system, self.w_sim, self.w_traffic, self.w_devices,
                  self.w_wifi, self.w_logs, self.w_misc):
            try: w.stop(); w.quit(); w.wait(500)
            except Exception as e:
                debug_log.exc(f"worker stop failed: {e}", "hub")
        try: self.client.close()
        except Exception as e:
            debug_log.exc(f"client.close failed: {e}", "hub")


# helper to launch design with Qt app
def run_design(design_class, design_name="FiberGuard"):
    """Standard launcher. design_class(hub) → main window.
    Now: prompts login on first run, auto-loads saved creds afterward,
    applies saved theme before any widget is constructed."""
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from PyQt5.QtCore    import Qt
    from PyQt5.QtWidgets import QApplication, QDialog
    from shared.login_view import LoginDialog
    from shared import auth_store, themes as theme_mod, i18n, preflight
    from shared.preflight_view import PreflightDialog

    # Bring up the logger before anything else can emit messages, then
    # install a global crash hook so even un-Qt-handled exceptions land
    # in app.log instead of vanishing.
    debug_log.init()
    debug_log.install_excepthook()
    debug_log.info(f"run_design called: design={design_name}", "boot")

    class SafeApp(QApplication):
        def notify(self, recv, ev):
            try: return super().notify(recv, ev)
            except Exception as e:
                debug_log.exc(f"Qt event delivery: {e}", "qt")
                return False

    # Force the Chromium child process to skip GPU init — many Windows
    # systems (especially headless servers / fresh installs) lack a usable
    # OpenGL driver and the GPU sandbox crashes immediately when fast.com
    # tries to render. Must be set BEFORE QtWebEngineWidgets is imported.
    os.environ.setdefault(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "--disable-gpu --no-sandbox "
        "--disable-features=UseChromeOSDirectVideoDecoder")

    # QtWebEngine demands a shared OpenGL context across all top-level
    # widgets, AND the attribute must be set before QApplication is built.
    # Skipping this is the #1 cause of "fast.com window crashes the app".
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # Pre-import the WebEngine bridge so Qt registers its meta types in the
    # right order. Wrapping in try/except keeps the launcher tolerant of
    # environments where PyQtWebEngine isn't installed.
    try:
        import PyQt5.QtWebEngineWidgets  # noqa: F401
    except Exception as e:
        debug_log.warn(f"QtWebEngine import failed; speed test disabled: {e}",
                        "boot")

    app = SafeApp(sys.argv)
    app.setApplicationName(design_name)
    app.setStyle("Fusion")

    # Apply saved theme + language BEFORE any widgets so the login dialog inherits both.
    saved_theme = auth_store.get_pref("theme", "light")
    theme_mod.set_theme(saved_theme)
    theme_mod.apply_palette(app)         # Fusion uses palette colors for inputs
    app.setStyleSheet(theme_mod.app_qss())
    saved_lang = auth_store.get_pref("lang", "en")
    i18n.set_lang(saved_lang)
    from PyQt5.QtCore import Qt as _Qt
    app.setLayoutDirection(_Qt.RightToLeft if saved_lang == "ar" else _Qt.LeftToRight)
    debug_log.info(f"theme={saved_theme}, lang={saved_lang}", "boot")

    # Preflight: verify VC++ runtime / router / internet / config dir.
    # Skip when a recent (≤30d) pass-flag exists, otherwise show the dialog.
    if not preflight.passed_recently():
        debug_log.info("preflight: no recent pass — showing dialog", "boot")
        pf = PreflightDialog()
        if pf.exec_() != QDialog.Accepted:
            debug_log.info("preflight: user cancelled — exiting", "boot")
            sys.exit(0)
    else:
        debug_log.info("preflight: skipped (recent pass cached)", "boot")

    # Resolve credentials: saved → use; else prompt.
    user, pwd, _ = auth_store.load_credentials()
    if not (user and pwd):
        debug_log.info("no saved credentials — showing login dialog", "boot")
        dlg = LoginDialog()
        if dlg.exec_() != QDialog.Accepted or not dlg.accepted_data:
            debug_log.info("login dialog cancelled — exiting", "boot")
            sys.exit(0)
        user, pwd, remember = dlg.accepted_data
        if remember:
            auth_store.save_credentials(user, pwd)
            debug_log.info("credentials saved (remember=True)", "boot")
    else:
        debug_log.info(f"using saved credentials for user={user}", "boot")

    hub = DataHub(user=user, pwd=pwd)
    win = design_class(hub)
    win.show(); win.raise_(); win.activateWindow()
    app._refs = (hub, win)
    hub.start()
    debug_log.info("entering Qt event loop", "boot")

    # Wire shutdown banner — fires when QApplication.quit() is called.
    app.aboutToQuit.connect(debug_log.shutdown_banner)

    sys.exit(app.exec_())
