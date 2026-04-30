"""FiberHome LG6851F — CDP-based client (headless Edge, encrypted FHAPIS via $post)."""

import json
import os
import subprocess
import time
import urllib.request
import threading
from typing import Any, Optional

def _find_edge() -> str:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return candidates[0]  # fallback

EDGE_PATH = _find_edge()
CDP_PORT  = 9223
CDP_DIR   = r"C:\Temp\fiberguard_cdp"


class RouterClient:
    def __init__(self, ip: str = "192.168.8.1"):
        self.ip        = ip
        self._proc     = None
        self._ws       = None
        self._ws_lock  = threading.RLock()
        self._eval_lock = threading.Lock()  # serialize JS calls
        self._msg_id   = 0
        self._pending  = {}   # id -> threading.Event + result
        self._recv_thr = None
        self.logged_in  = False
        self.dev_mode   = False
        self.last_error = ""

    # ── browser lifecycle ────────────────────────────────────────────────────

    def _log(self, msg):
        try:
            with open(r"C:\Temp\fiberguard_log.txt", "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    def _launch_edge(self):
        self._log(f"_launch_edge: EDGE_PATH={EDGE_PATH}")
        self._log(f"_launch_edge: Edge exists={os.path.isfile(EDGE_PATH)}")
        os.makedirs(CDP_DIR, exist_ok=True)
        cmd = [
            EDGE_PATH,
            f"--remote-debugging-port={CDP_PORT}",
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-web-security",
            "--remote-allow-origins=*",
            f"--user-data-dir={CDP_DIR}",
            "about:blank",
        ]
        try:
            self._proc = subprocess.Popen(
                cmd,
                creationflags=0x08000000,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._log(f"_launch_edge: Edge PID={self._proc.pid}")
        except Exception as e:
            self._log(f"_launch_edge: Popen failed: {e}")
            return False

        for i in range(30):
            try:
                urllib.request.urlopen(
                    f"http://localhost:{CDP_PORT}/json/version", timeout=1
                )
                self._log(f"_launch_edge: CDP ready at attempt {i+1}")
                return True
            except Exception:
                time.sleep(0.4)
        self._log("_launch_edge: CDP timeout")
        return False

    def _get_tab_ws(self) -> Optional[str]:
        try:
            raw = urllib.request.urlopen(
                f"http://localhost:{CDP_PORT}/json", timeout=5
            ).read().decode()
            tabs = json.loads(raw)
            for t in tabs:
                if t.get("type") == "page":
                    return t.get("webSocketDebuggerUrl")
            # create new tab
            urllib.request.urlopen(
                f"http://localhost:{CDP_PORT}/json/new", timeout=5
            )
            time.sleep(0.5)
            raw = urllib.request.urlopen(
                f"http://localhost:{CDP_PORT}/json", timeout=5
            ).read().decode()
            tabs = json.loads(raw)
            for t in tabs:
                if t.get("type") == "page":
                    return t.get("webSocketDebuggerUrl")
        except Exception as e:
            self.last_error = str(e)
        return None

    def _connect_ws(self, ws_url: str) -> bool:
        try:
            self._log(f"_connect_ws: connecting to {ws_url[:60]}")
            from ws_client import SimpleWS
            self._ws = SimpleWS()
            self._ws.connect(ws_url, timeout=10)
            self._log("_connect_ws: connected OK")
            self._recv_thr = threading.Thread(
                target=self._recv_loop, daemon=True
            )
            self._recv_thr.start()
            return True
        except Exception as e:
            self._log(f"_connect_ws: FAILED {e}")
            self.last_error = str(e)
            return False

    def _recv_loop(self):
        while True:
            try:
                raw = self._ws.recv()
                if not raw:
                    break
                msg = json.loads(raw)
                mid = msg.get("id")
                if mid:
                    with self._ws_lock:
                        entry = self._pending.get(mid)
                        if entry is not None:
                            ev, _ = entry
                            self._pending[mid] = (ev, msg)
                            ev.set()
            except Exception as e:
                self._log(f"_recv_loop exit: {e}")
                break
        # signal all pending waiters so they don't hang
        try:
            with self._ws_lock:
                for mid, (ev, _) in list(self._pending.items()):
                    self._pending[mid] = (ev, {"error": "ws disconnected"})
                    ev.set()
        except Exception:
            pass

    def _send(self, method: str, params: dict = None, timeout: float = 20.0) -> dict:
        with self._ws_lock:
            self._msg_id += 1
            mid = self._msg_id
            msg = json.dumps({"id": mid, "method": method,
                              "params": params or {}})
            ev = threading.Event()
            self._pending[mid] = (ev, None)
        try:
            self._ws.send(msg)
        except Exception as e:
            with self._ws_lock:
                self._pending.pop(mid, None)
            return {"error": str(e)}
        ev.wait(timeout)
        with self._ws_lock:
            _, result = self._pending.pop(mid, (None, {}))
        return result or {}

    # ── JS execution helpers ─────────────────────────────────────────────────

    def _eval(self, js: str, timeout: float = 20.0) -> Any:
        r = self._send("Runtime.evaluate", {
            "expression":            js,
            "awaitPromise":          True,
            "returnByValue":         True,
            "generatePreview":       False,
            "timeout":               int(timeout * 1000),
        }, timeout=timeout + 2)
        res = r.get("result", {}).get("result", {})
        if res.get("type") == "string":
            return res["value"]
        if res.get("type") in ("number", "boolean"):
            return res["value"]
        if res.get("type") == "object":
            val = res.get("value")
            if val is not None:
                return val
            # try subtype / description fallback
            return res.get("description", "")
        return None

    def _eval_json(self, js: str, timeout: float = 20.0) -> Any:
        wrapped = f"""
(async () => {{
    const __r = await ({js});
    return JSON.stringify(__r);
}})()
"""
        raw = self._eval(wrapped, timeout=timeout)
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return raw
        return raw

    # ── public API ───────────────────────────────────────────────────────────

    def login(self, username: str = "superadmin", password: str = "F1ber$dm",
              status_cb=None) -> bool:
        def _status(msg):
            self.last_error = msg
            if status_cb:
                status_cb(msg)

        # تشغيل Edge
        _status("جاري تشغيل المتصفح…")
        try:
            urllib.request.urlopen(
                f"http://localhost:{CDP_PORT}/json/version", timeout=1
            )
        except Exception:
            ok = self._launch_edge()
            if not ok:
                self.last_error = "تعذر تشغيل Edge"
                return False

        ws_url = self._get_tab_ws()
        if not ws_url:
            self.last_error = "لا يوجد تبويب CDP"
            return False

        if not self._connect_ws(ws_url):
            return False

        self._send("Runtime.enable")
        self._send("Page.enable")

        _status("جاري فتح صفحة الراوتر…")
        self._send("Page.navigate",
                   {"url": f"http://{self.ip}/login.html"},
                   timeout=15)
        time.sleep(4)

        # perform login
        login_js = f"""
(async () => {{
    try {{
        g_this.formData.LoginName = {json.dumps(username)};
        g_this.formData.LoginPwd  = {json.dumps(password)};
        g_this.onApply();
        await new Promise(r => setTimeout(r, 5000));
        return "ok";
    }} catch(e) {{
        return "err:" + e.message;
    }}
}})()
"""
        _status("جاري تسجيل الدخول…")
        result = self._eval(login_js, timeout=20)
        if isinstance(result, str) and result.startswith("err:"):
            self.last_error = result[4:]
            self.logged_in  = False
            return False

        time.sleep(1)
        _status("جاري تفعيل وضع المطور…")
        # enter developer mode
        dev_js = f"""
(async () => {{
    try {{
        const r = await $post('enter_developer',
            {{user: 3, password: {json.dumps(password)}}});
        return JSON.stringify(r);
    }} catch(e) {{
        return "err:" + e.message;
    }}
}})()
"""
        dev_raw = self._eval(dev_js, timeout=15)
        if isinstance(dev_raw, str) and not dev_raw.startswith("err:"):
            try:
                d = json.loads(dev_raw)
                if d.get("developer_flag") == 1:
                    self.dev_mode = True
            except Exception:
                pass

        self.logged_in  = True
        return True

    def keepalive(self):
        if not self.logged_in:
            return
        try:
            self._eval_json("$post('get_header_info', {})", timeout=10)
            if not self.dev_mode:
                dev_js = """
(async () => {
    const r = await $post('enter_developer', {user:3, password:'F1ber$dm'});
    return JSON.stringify(r);
})()
"""
                raw = self._eval(dev_js, timeout=10)
                if isinstance(raw, str):
                    try:
                        if json.loads(raw).get("developer_flag") == 1:
                            self.dev_mode = True
                    except Exception:
                        pass
        except Exception:
            pass

    def _ensure_connected(self):
        """Check WebSocket. Do NOT silently reconnect — that breaks active sessions."""
        try:
            if self._ws and self._ws.connected:
                return True
        except Exception:
            pass
        return False

    def _post_api(self, method: str, data: dict = None, timeout: float = 18.0) -> Any:
        if not self._ensure_connected():
            return {}
        data_js = json.dumps(data) if data else "null"
        js = f"""
(async () => {{
    const d = {data_js};
    const r = d ? await $post({json.dumps(method)}, d)
                : await $post({json.dumps(method)});
    return JSON.stringify(r);
}})()
"""
        with self._eval_lock:
            raw = self._eval(js, timeout=timeout)
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return raw
        return raw

    def _post_multi(self, calls: list, timeout: float = 18.0) -> dict:
        """Equivalent to router's $multipost — fires N posts in one round-trip.
        calls = [(method, data_dict_or_None), ...]
        Returns {"data_1": resp1, "data_2": resp2, ...}.
        """
        if not self._ensure_connected() or not calls:
            return {}
        methods = "|".join(m for m, _ in calls)
        args_js = ", ".join(json.dumps(d if d is not None else {}) for _, d in calls)
        js = f"""
(async () => {{
    const r = await $multipost({json.dumps(methods)}, {args_js});
    return JSON.stringify(r);
}})()
"""
        with self._eval_lock:
            raw = self._eval(js, timeout=timeout)
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return {}
        return raw or {}

    def send_at(self, command: str) -> str:
        r = self._post_api("set_at_command", {"command": command})
        if isinstance(r, dict):
            for k in ("result", "response", "output", "data", "Result"):
                if k in r:
                    return str(r[k])
            return json.dumps(r)
        return str(r) if r else ""

    def cmd_result(self, key: str) -> str:
        r = self._post_api("get_cmd_result_web", {"key": key})
        if isinstance(r, dict):
            return str(r.get("result", r.get("data", r.get("value", ""))))
        return str(r) if r else ""

    def xmlnode(self, path: str) -> Any:
        return self._post_api("get_value_by_xmlnode", {"path": path})

    def get_logs(self, level: int = 7) -> Any:
        return self._post_api("log_view", {"LogViewLevel": str(level)})

    def get_version(self) -> Any:
        return self._post_api("version_detection")

    def get_header(self) -> Any:
        return self._post_api("get_header_info")

    # ── cleanup ──────────────────────────────────────────────────────────────

    def close(self):
        self.logged_in = False
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        try:
            if self._proc:
                self._proc.terminate()
        except Exception:
            pass
