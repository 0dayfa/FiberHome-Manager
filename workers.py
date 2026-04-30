"""Background QThread workers."""
import time
import traceback
from PyQt5.QtCore import QThread, pyqtSignal
from api_client import RouterClient
import router_api as api
from shared import debug_log


def _log(msg):
    """Legacy alias retained for any old call sites — routes to debug_log."""
    debug_log.info(msg, "worker")


class _BaseWorker(QThread):
    """Base poller — child overrides _fetch()."""
    data = pyqtSignal(object)
    def __init__(self, client, interval_ms):
        super().__init__()
        self.client = client
        self.interval = interval_ms / 1000.0
        self._running = True
    def _fetch(self): pass
    def run(self):
        try:
            while self._running:
                if self.client.logged_in:
                    try:
                        d = self._fetch()
                        if d is not None:
                            self.data.emit(d)
                    except Exception as e:
                        _log(f"{type(self).__name__} EXC: {e}")
                time.sleep(self.interval)
        except Exception as e:
            _log(f"{type(self).__name__} FATAL: {e}\n{traceback.format_exc()}")
    def stop(self): self._running = False


# ────────────────────────────── Auth ──────────────────────────────
class AuthWorker(QThread):
    status = pyqtSignal(bool, str)
    def __init__(self, client, username, password):
        super().__init__()
        self.client, self.username, self.password = client, username, password
        self._running = True
    def run(self):
        try:
            debug_log.info(f"login attempt → {self.client.ip} as {self.username}",
                            "auth")
            ok = self.client.login(self.username, self.password,
                                    status_cb=lambda m: self.status.emit(False, m))
            self.status.emit(bool(ok),
                "Connected" if ok else self.client.last_error or "Login failed")
            debug_log.info(f"login result: {'success' if ok else 'failed'} "
                            f"({self.client.last_error or 'OK'})", "auth")
        except Exception as e:
            debug_log.exc(f"AuthWorker exception: {e}", "auth")
            self.status.emit(False, str(e)[:60])
        last = time.time()
        while self._running:
            time.sleep(1)
            if time.time() - last >= 30:
                try: self.client.keepalive()
                except Exception: pass
                last = time.time()
    def stop(self): self._running = False


# ────────────────────────────── Specific workers ──────────────────────────────
class HeaderWorker(_BaseWorker):
    def _fetch(self): return api.get_header(self.client)

class RadioWorker(_BaseWorker):
    def _fetch(self):
        r = api.get_radio(self.client)
        if r:
            r["_neighbors"] = api.parse_neighbors(r)
        return r

class CAWorker(_BaseWorker):
    def _fetch(self): return api.get_ca(self.client)

class SystemWorker(_BaseWorker):
    def _fetch(self):
        out = api.get_system(self.client) or {}
        ut = api.get_uptime(self.client)
        if ut:
            out["uptime_raw"] = ut
            out["uptime_fmt"] = api.fmt_uptime_seconds(ut.split(".")[0] if "." in ut else ut)
        dt = api.get_date(self.client)
        if dt: out["date"] = dt.strip()
        return out if out else None

class SimWorker(_BaseWorker):
    def _fetch(self):
        sim = api.get_sim(self.client) or {}
        pin = api.get_pin(self.client) or {}
        out = dict(sim); out["_pin"] = pin
        return out

class TrafficWorker(_BaseWorker):
    def _fetch(self): return api.get_traffic(self.client)

class DevicesWorker(_BaseWorker):
    def _fetch(self): return api.get_devices(self.client)

class WiFiWorker(_BaseWorker):
    def _fetch(self):
        return {
            "ssids":  api.get_wifi_ssids(self.client),
            "aps":    api.get_wifi_aps(self.client),
            "radios": api.get_wifi_radios(self.client),
        }


class LogWorker(QThread):
    new_lines = pyqtSignal(object)
    def __init__(self, client, interval_ms=20000):
        super().__init__()
        self.client = client
        self.interval = interval_ms / 1000.0
        self._running = True
        self._seen = set()
    def run(self):
        try:
            while self._running:
                if self.client.logged_in:
                    try:
                        r = self.client.get_logs(7)
                        text = ""
                        if isinstance(r, dict):
                            for k in sorted(r.keys()):
                                if k.startswith("log"):
                                    text += str(r[k]) + "\n"
                        elif isinstance(r, str):
                            text = r
                        new = []
                        for ln in text.split("\n"):
                            ln = ln.strip()
                            if ln and ln not in self._seen:
                                self._seen.add(ln)
                                new.append(ln)
                        if new: self.new_lines.emit(new)
                    except Exception as e:
                        _log(f"LogWorker EXC: {e}")
                time.sleep(self.interval)
        except Exception as e:
            _log(f"LogWorker FATAL: {e}")
    def stop(self): self._running = False


class MiscWorker(_BaseWorker):
    """LAN, WAN_IP, Firewall, ALG, TR069, antenna, network-detection, debug, network-settings"""
    def _fetch(self):
        out = {}
        for name, fn in [
                ("lan",      api.get_lan),
                ("wan_ip",   api.get_wan_ip_info),
                ("firewall", api.get_firewall),
                ("alg",      api.get_alg),
                ("tr069",    api.get_tr069),
                ("antenna",  api.get_antenna),
                ("net_detect",api.get_network_detection),
                ("debug",    api.get_debug_state),
                ("priv_net", api.get_private_network),
                ("net_set",  api.get_network_settings),
                ("car_lock", api.get_carrier_lock),
        ]:
            try: out[name] = fn(self.client) or {}
            except Exception: pass
        return out
