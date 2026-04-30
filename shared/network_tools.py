"""Public IP lookup + Cloudflare speed test (no third-party deps).

Cloudflare's speed.cloudflare.com endpoints are publicly available with no
auth, hit the user's nearest edge POP (300+ globally), and the same engine
their own speed test page uses — so accuracy matches what the user sees in
a browser at speed.cloudflare.com.
"""
import urllib.request
import urllib.error
import json
import time
import ssl
import socket


# Some carrier-grade middleboxes break TLS validation, and we're only
# fetching public speed-test endpoints — so don't fail the test for that.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode  = ssl.CERT_NONE

_UA = "FiberGuard/1.0 (+https://routers.world)"

_PUBLIC_IP_SOURCES = [
    ("https://api.ipify.org?format=json",  lambda r: json.loads(r).get("ip", "")),
    ("https://ipv4.icanhazip.com/",        lambda r: r.strip()),
    ("https://ipinfo.io/json",             lambda r: json.loads(r).get("ip", "")),
    ("https://api64.ipify.org?format=json",lambda r: json.loads(r).get("ip", "")),
]


def _is_ipv4(s: str) -> bool:
    parts = s.split(".")
    if len(parts) != 4: return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def fetch_public_ip(timeout: float = 5.0) -> str:
    """Try every source in order; return the first valid IPv4 string,
    or '' if every source fails (offline / firewalled)."""
    for url, parser in _PUBLIC_IP_SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
                txt = r.read().decode("utf-8", errors="replace")
            ip = parser(txt).strip()
            if _is_ipv4(ip):
                return ip
        except Exception:
            continue
    return ""


# ───── Cloudflare speed test ─────
_CF_BASE = "https://speed.cloudflare.com"


def measure_ping(timeout: float = 5.0, samples: int = 5) -> float:
    """Median ping in ms via repeated tiny GETs to CF's trace endpoint.
    Median (not min/avg) is the resilient choice — it ignores warm-up
    spikes and the occasional rogue request."""
    samples_ms = []
    for _ in range(samples):
        try:
            t0 = time.perf_counter()
            req = urllib.request.Request(f"{_CF_BASE}/cdn-cgi/trace",
                                          headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
                r.read(64)  # 200 OK is enough; don't drain whole body
            samples_ms.append((time.perf_counter() - t0) * 1000.0)
        except Exception:
            continue
    if not samples_ms:
        return 0.0
    samples_ms.sort()
    return samples_ms[len(samples_ms) // 2]


def measure_download(target_bytes: int = 25_000_000,
                      timeout: float = 30.0) -> tuple:
    """Download N bytes from CF, return (mbps, bytes_read, seconds).
    Uses 64KB chunks; the connection limits transfer rate to the user's
    actual line speed — that's the measurement."""
    url = f"{_CF_BASE}/__down?bytes={int(target_bytes)}"
    t0 = time.perf_counter()
    total = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
            while True:
                chunk = r.read(64 * 1024)
                if not chunk: break
                total += len(chunk)
    except Exception:
        pass
    elapsed = max(time.perf_counter() - t0, 0.001)
    mbps = (total * 8.0) / elapsed / 1_000_000.0
    return mbps, total, elapsed


def measure_upload(target_bytes: int = 10_000_000,
                    timeout: float = 30.0) -> tuple:
    """Upload N bytes to CF, return (mbps, bytes_sent, seconds)."""
    url = f"{_CF_BASE}/__up"
    payload = b"\0" * int(target_bytes)
    t0 = time.perf_counter()
    sent = 0
    try:
        req = urllib.request.Request(url, data=payload, method="POST",
            headers={"Content-Type": "application/octet-stream",
                      "User-Agent": _UA,
                      "Content-Length": str(len(payload))})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
            r.read()
            sent = len(payload)
    except Exception:
        pass
    elapsed = max(time.perf_counter() - t0, 0.001)
    mbps = (sent * 8.0) / elapsed / 1_000_000.0
    return mbps, sent, elapsed
