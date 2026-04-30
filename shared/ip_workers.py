"""Background workers for the IP Scan page.

Three threads:
    IpMonitorWorker   — polls WAN/Public IP every N seconds
    IpChangeWorker    — toggles airplane mode (ON → wait → OFF → wait)
    SpeedTestWorker   — Cloudflare ping + download + upload

Each emits qt signals; the page wires them to log lines and chip refreshes.
Workers are deliberately simple — no shared state, no locks — so the
controller in the page (the Python thread that owns the QThread objects)
is the single decision point for "what runs next" (e.g. auto speed test,
IP pinning).
"""
import time
from PyQt5.QtCore import QThread, pyqtSignal

from shared.network_tools import (fetch_public_ip, measure_ping,
                                    measure_download, measure_upload)
import router_api as rapi


class IpMonitorWorker(QThread):
    """Periodic snapshot of WAN IP + connection status + public IP."""
    update = pyqtSignal(dict)   # {status, wan_ip, public_ip, ts}

    def __init__(self, client, interval_ms=2000):
        super().__init__()
        self.client = client
        self.interval = max(0.5, interval_ms / 1000.0)
        self._running = True

    def run(self):
        while self._running:
            try:
                wan_info = rapi.get_wan_ip_info(self.client) or {}
                wan_ip = str(wan_info.get("ExternalIPAddress", "") or "").strip()
                conn   = str(wan_info.get("ConnectionStatus", "") or "").strip()

                # Normalise the firmware's English variants ("Connected",
                # "Connecting", "Disconnected") to a stable 3-state vocab.
                low = conn.lower()
                if "connect" in low and "dis" not in low and "ing" not in low:
                    status = "Connected"
                elif "connecting" in low:
                    status = "Connecting"
                elif "disconnect" in low or low in ("", "down", "no"):
                    status = "Disconnected"
                else:
                    status = conn or "Unknown"

                public_ip = fetch_public_ip() if status == "Connected" else ""

                self.update.emit({
                    "status":    status,
                    "wan_ip":    wan_ip or "Unknown",
                    "public_ip": public_ip or ("" if status == "Connected" else "—"),
                    "ts":        time.time(),
                })
            except Exception:
                pass
            # Sleep in small slices so .stop() has snappy response.
            slept = 0.0
            while slept < self.interval and self._running:
                time.sleep(0.2); slept += 0.2

    def stop(self):
        self._running = False


class IpChangeWorker(QThread):
    """Airplane-mode toggle to force a fresh WAN IP from the carrier.
    Sequence matches what the original userscript does manually:
        ON  → wait 8s  →  OFF  →  wait 3s reconnect
    """
    progress = pyqtSignal(str)         # human-readable status text
    done     = pyqtSignal(bool, str)   # (success, message)

    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self):
        try:
            self.progress.emit("Enabling airplane mode…")
            rapi.set_airplane(self.client, True)
            for i in range(8, 0, -1):
                self.progress.emit(f"Waiting {i}s for cell to drop…")
                self.msleep(1000)

            self.progress.emit("Disabling airplane mode…")
            rapi.set_airplane(self.client, False)
            self.progress.emit("Reconnecting…")
            self.msleep(3000)
            self.done.emit(True, "IP change complete")
        except Exception as e:
            self.done.emit(False, str(e)[:120])


class SpeedTestWorker(QThread):
    """Cloudflare ping + download + upload, in that order.
    The download warmup also primes TCP windows for the upload — picking
    smaller upload payload (10MB vs 25MB down) keeps the whole test under
    ~30 seconds on most connections."""
    progress = pyqtSignal(str)
    done     = pyqtSignal(dict)        # {download, upload, ping}  OR  {error}

    def __init__(self, dl_bytes=25_000_000, ul_bytes=10_000_000):
        super().__init__()
        self.dl_bytes = dl_bytes
        self.ul_bytes = ul_bytes

    def run(self):
        try:
            self.progress.emit("Pinging Cloudflare…")
            ping = measure_ping()
            self.progress.emit("Testing download…")
            dl, _, dl_sec = measure_download(self.dl_bytes)
            self.progress.emit("Testing upload…")
            ul, _, ul_sec = measure_upload(self.ul_bytes)
            self.done.emit({
                "download": round(dl, 2),
                "upload":   round(ul, 2),
                "ping":     round(ping, 1),
                "dl_sec":   round(dl_sec, 1),
                "ul_sec":   round(ul_sec, 1),
            })
        except Exception as e:
            self.done.emit({"error": str(e)[:120]})


def ip_matches(ip: str, pattern: str) -> bool:
    """Pattern grammar from the original userscript:
        '10.193.89'    → prefix match: ip.startswith('10.193.89')
        '1x2x3'        → exclude: ip's first octet is NOT 1, 2 or 3
        '10-20-30'     → include: ip's first octet IS 10, 20 or 30
    Returns False on Unknown / empty IPs."""
    if not ip or ip in ("Unknown", "Failed!", "—", ""): return False
    if not pattern: return False
    if "x" in pattern:
        excluded = [s.strip() for s in pattern.split("x") if s.strip()]
        return ip.split(".")[0] not in excluded
    if "-" in pattern:
        allowed = [s.strip() for s in pattern.split("-") if s.strip()]
        return ip.split(".")[0] in allowed
    return ip.startswith(pattern)
