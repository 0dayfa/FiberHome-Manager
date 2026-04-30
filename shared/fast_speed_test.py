"""Hidden Fast.com speed test driver.

Loads fast.com inside an off-screen QWebEngineView, polls the DOM with a
small JS reader until the test is done, then returns the same numbers a
human would see on screen.

Why a hidden browser instead of a Cloudflare HTTP probe? Fast.com saturates
multiple parallel connections to the carrier's nearest Netflix Open Connect
appliance — that path differs from Cloudflare's POPs and matches what most
users measure as "their speed". Cloudflare numbers can underread by 3-5×
for users behind certain MNO peering arrangements.

The runner is a QObject, not a QThread — QWebEngineView must run on the
GUI thread. Background work happens via QTimer ticks instead.
"""
import os

# Force the Chromium child to use software rendering. On stock Windows
# installs without an OpenGL driver, GPU init can SIGSEGV the renderer
# immediately on view creation — and that takes the whole Qt process down
# with it. Software rendering is plenty fast for a JS-driven speed test.
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-software-rasterizer --no-sandbox "
    "--disable-features=UseChromeOSDirectVideoDecoder")

from PyQt5.QtCore import QObject, QUrl, QTimer, pyqtSignal, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage


# Inject this script every poll. It re-reads the DOM and stuffs the latest
# numbers into window.__fast_state so we can fish them out via runJavaScript.
_PROBE = """
(function () {
    const speedEl   = document.querySelector('#speed-value');
    const uploadEl  = document.querySelector('#upload-value');
    const pingEl    = document.querySelector('#latency-value');
    const moreLink  = document.querySelector('#show-more-details-link');
    const progress  = document.querySelector('#speed-progress-indicator');
    const noConn    = document.querySelector('div#error-results-msg[loc-str="no_connection"]');

    // After the download phase succeeds, click "show more details" once to
    // unlock the upload + latency panels.
    if (progress && progress.classList.contains('succeeded') &&
        !progress.classList.contains('in-progress') && moreLink &&
        moreLink.style.display !== 'none' && !window.__fast_clicked) {
        try { moreLink.click(); window.__fast_clicked = true; } catch (e) {}
    }

    const noConnVisible = noConn && noConn.offsetParent !== null;
    const uploadDone = uploadEl &&
                        uploadEl.classList.contains('succeeded') &&
                        uploadEl.textContent.trim() !== '0';

    const out = {
        download:       speedEl  ? (speedEl.textContent  || '').trim() : '',
        upload:         uploadEl ? (uploadEl.textContent || '').trim() : '',
        ping:           pingEl   ? (pingEl.textContent   || '').trim() : '',
        downloadDone:   progress ? progress.classList.contains('succeeded') &&
                                    !progress.classList.contains('in-progress') : false,
        uploadDone:     !!uploadDone,
        noConnVisible:  !!noConnVisible,
    };
    window.__fast_state = out;
    return out;
})();
"""


class FastSpeedTest(QObject):
    """Drive a hidden fast.com page; emit `progress(text)` and `done(dict)`."""

    progress = pyqtSignal(str)
    done     = pyqtSignal(dict)   # {download, upload, ping}  OR  {error}

    def __init__(self, parent=None, timeout_sec=120):
        super().__init__(parent)
        self._timeout = timeout_sec
        self._view    = None
        self._poll    = None
        self._giveup  = None
        self._fired   = False
        self._zero_streak = 0           # tracks "all-zero with no_connection"
        self._poll_count  = 0

    # ── Public API ──
    def start(self):
        if self._view is not None: return
        self._fired = False
        self._zero_streak = 0
        self._poll_count = 0

        self._view = QWebEngineView()
        # Off-screen geometry + Tool window flag → never appears on screen
        # but Qt still gives the page a real renderer & can run JS.
        self._view.setAttribute(Qt.WA_DontShowOnScreen, True)
        self._view.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self._view.resize(1024, 768)
        self._view.show()             # required for the renderer to tick
        self._view.move(-3000, -3000)  # belt-and-braces — keep it offscreen

        page = self._view.page()
        page.loadFinished.connect(self._on_loaded)
        self.progress.emit("Opening fast.com…")
        self._view.setUrl(QUrl("https://fast.com/"))

        # Hard timeout — fast.com takes ~25s normally, allow 2 minutes.
        self._giveup = QTimer(self)
        self._giveup.setSingleShot(True)
        self._giveup.timeout.connect(self._on_timeout)
        self._giveup.start(self._timeout * 1000)

    def stop(self):
        for t in (self._poll, self._giveup):
            if t and t.isActive(): t.stop()
        self._poll = self._giveup = None
        if self._view is not None:
            try:
                self._view.stop()
                self._view.setUrl(QUrl("about:blank"))
                self._view.close()
                self._view.deleteLater()
            except Exception: pass
            self._view = None

    # ── Internals ──
    def _on_loaded(self, ok):
        if not ok:
            self._finish({"error": "Failed to load fast.com"})
            return
        self.progress.emit("Running speed test…")
        # Poll DOM ~every 800ms (matches the Tampermonkey original).
        self._poll = QTimer(self)
        self._poll.setInterval(800)
        self._poll.timeout.connect(self._tick)
        self._poll.start()

    def _tick(self):
        if self._fired or self._view is None: return
        self._poll_count += 1
        try:
            self._view.page().runJavaScript(_PROBE, self._on_probe)
        except Exception:
            pass

    def _on_probe(self, state):
        if self._fired or not isinstance(state, dict): return

        dl  = (state.get("download") or "0").strip()
        ul  = (state.get("upload")   or "0").strip()
        pg  = (state.get("ping")     or "0").strip()
        dl_done = bool(state.get("downloadDone"))
        ul_done = bool(state.get("uploadDone"))
        no_conn = bool(state.get("noConnVisible"))

        # No-connection screen → bail out early.
        if no_conn and dl == "0" and ul == "0" and pg == "0":
            self._zero_streak += 1
            if self._zero_streak >= 6:   # ~5s of solid no-conn
                self._finish({"error": "fast.com reported no connection"})
            return
        else:
            self._zero_streak = 0

        # Status updates while we wait
        if dl_done and not ul_done:
            self.progress.emit(f"Download: {dl} Mbps · waiting upload…")
        elif not dl_done:
            self.progress.emit(f"Download: {dl or '0'} Mbps…")

        # Done condition — both phases succeeded with non-zero numbers.
        if dl_done and ul_done and dl not in ("", "0") \
                and ul not in ("", "0") and pg not in ("", "0"):
            self._finish({
                "download": _safe_float(dl),
                "upload":   _safe_float(ul),
                "ping":     _safe_float(pg),
            })

    def _on_timeout(self):
        if self._fired: return
        self._finish({"error": "Speed test timeout"})

    def _finish(self, payload):
        if self._fired: return
        self._fired = True
        # Tear down BEFORE emitting — caller may start another run on done.
        try:
            if self._poll and self._poll.isActive(): self._poll.stop()
            if self._giveup and self._giveup.isActive(): self._giveup.stop()
        except Exception: pass
        # Defer view destruction until after this signal handler returns —
        # tearing down a QWebEngineView from inside its own JS callback can
        # crash on some Qt builds.
        QTimer.singleShot(0, self._cleanup_view)
        self.done.emit(payload)

    def _cleanup_view(self):
        if self._view is None: return
        try:
            self._view.stop()
            self._view.setUrl(QUrl("about:blank"))
            self._view.close()
            self._view.deleteLater()
        except Exception: pass
        self._view = None


def _safe_float(s):
    try: return round(float(s), 2)
    except Exception: return 0.0
