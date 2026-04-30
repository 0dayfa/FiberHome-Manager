"""First-run system preflight.

The PyInstaller bundle ships its own Python and PyQt5/PyQtWebEngine, so
the user does NOT need to install any of those. The real failure modes
on a fresh Windows machine are:

    1.  Microsoft Visual C++ Redistributable missing (vcruntime140.dll)
    2.  Router not reachable on the LAN (wrong IP, not connected)
    3.  No internet (IP Scan + Speed Test won't work)
    4.  Config dir not writable (saved login won't persist)

This module performs those checks. The companion preflight_view.py
renders the UI; this file stays pure-stdlib so it can be unit-tested.
"""
import os
import socket
import ssl
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


# Microsoft's stable redirect to the latest x64 redist installer.
VC_RUNTIME_URL    = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
DEFAULT_ROUTER_IP = "192.168.8.1"


# ───── Individual checks ─────
def check_vcredist() -> tuple:
    """Look for the runtime DLLs in System32. Either name on its own is
    enough — vcruntime140_1.dll appears only on newer CRT installs."""
    win_root = os.environ.get("SystemRoot", r"C:\Windows")
    paths = [
        os.path.join(win_root, "System32", "vcruntime140.dll"),
        os.path.join(win_root, "System32", "vcruntime140_1.dll"),
    ]
    found = [p for p in paths if os.path.isfile(p)]
    if found:
        return True, f"Found {len(found)} runtime DLL(s)"
    return False, "Visual C++ 2015-2022 Redistributable missing"


def check_router(ip: str = DEFAULT_ROUTER_IP, port: int = 80,
                  timeout: float = 3.0) -> tuple:
    """Plain TCP probe — no HTTP since some firmwares respond slowly to GET."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True, f"{ip}:{port} reachable"
    except OSError as e:
        return False, f"Cannot reach {ip}:{port} ({e.__class__.__name__})"
    except Exception as e:
        return False, f"Cannot reach {ip}:{port}: {e}"


def check_internet(timeout: float = 5.0) -> tuple:
    """Try a small GET against a few stable third-party endpoints.
    An HTTPError counts as "internet works" — getting an HTTP status
    back at all means we reached a server. We only fail when we can't
    even open a TCP connection."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    targets = [
        "https://www.cloudflare.com/cdn-cgi/trace",
        "https://api.ipify.org/",
        "https://ipv4.icanhazip.com/",
    ]
    last_err = None
    for url in targets:
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "FiberGuard-Preflight/1.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                r.read(64)  # don't drain — proof of connection is enough
            host = url.split("//", 1)[1].split("/", 1)[0]
            return True, f"Reachable via {host}"
        except urllib.error.HTTPError as e:
            # Server replied with an HTTP error — connection works.
            return True, f"Reachable (HTTP {e.code})"
        except Exception as e:
            last_err = e
            continue
    return False, f"No internet ({last_err.__class__.__name__})"


def check_config_writable() -> tuple:
    """Ensure %USERPROFILE%/.fiberguard exists and is writable."""
    d = Path.home() / ".fiberguard"
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True, str(d)
    except Exception as e:
        return False, f"Cannot write to {d}: {e}"


def all_checks() -> list:
    """Returns ordered list of (key, ok: bool, detail: str)."""
    return [
        ("vcredist", *check_vcredist()),
        ("router",   *check_router()),
        ("internet", *check_internet()),
        ("config",   *check_config_writable()),
    ]


# ───── Auto-installer for VC++ redist ─────
def install_vcredist() -> tuple:
    """Download Microsoft's stub installer and run it silently.
    Returns (ok, message). Exit codes:
        0     installed
        3010  installed, reboot required
        1638  newer version already installed (treat as success)
    """
    try:
        tmp_path = Path(tempfile.gettempdir()) / "vc_redist.x64.exe"
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(VC_RUNTIME_URL, timeout=120,
                                      context=ctx) as r:
            tmp_path.write_bytes(r.read())
    except Exception as e:
        return False, f"Download failed: {e}"
    try:
        rc = subprocess.run(
            [str(tmp_path), "/quiet", "/norestart"],
            timeout=600).returncode
    except Exception as e:
        return False, f"Installer failed to launch: {e}"
    if rc in (0, 1638, 3010):
        suffix = " (reboot required)" if rc == 3010 else ""
        return True, f"Installed{suffix}"
    return False, f"Installer returned exit code {rc}"


# ───── Cached "passed" flag ─────
PREFLIGHT_FLAG = Path.home() / ".fiberguard" / ".preflight_passed"
_FLAG_TTL_DAYS = 30


def passed_recently() -> bool:
    """True if preflight passed within the last 30 days. Time-bound so a
    new VC update / network change eventually re-prompts."""
    try:
        if not PREFLIGHT_FLAG.is_file(): return False
        age = time.time() - PREFLIGHT_FLAG.stat().st_mtime
        return age < _FLAG_TTL_DAYS * 86400
    except Exception:
        return False


def mark_passed():
    try:
        PREFLIGHT_FLAG.parent.mkdir(parents=True, exist_ok=True)
        PREFLIGHT_FLAG.write_text(time.strftime("%Y-%m-%d %H:%M:%S"),
                                    encoding="utf-8")
    except Exception:
        pass


def clear_pass_flag():
    try:
        if PREFLIGHT_FLAG.is_file(): PREFLIGHT_FLAG.unlink()
    except Exception:
        pass
