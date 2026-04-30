"""Persisted login + UI prefs at %USERPROFILE%/.fiberguard/config.json.

Credentials sit on the user's own machine alongside the app — same trust
boundary they live in inside the router web UI's autofill, so we keep them
in plain JSON rather than over-engineering encryption that the user could
trivially bypass anyway.
"""
import os, json
from pathlib import Path

CONFIG_DIR  = Path.home() / ".fiberguard"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _read() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write(d: dict):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    except Exception:
        pass


def load_credentials():
    """Returns (username, password, remembered: bool) or (None, None, False)."""
    d = _read()
    a = d.get("auth") or {}
    if a.get("user") and a.get("pwd"):
        return a["user"], a["pwd"], True
    return None, None, False


def save_credentials(user: str, pwd: str):
    d = _read()
    d.setdefault("auth", {})
    d["auth"]["user"] = user
    d["auth"]["pwd"]  = pwd
    _write(d)


def clear_credentials():
    d = _read()
    d.pop("auth", None)
    _write(d)


def get_pref(key: str, default=None):
    return _read().get(key, default)


def set_pref(key: str, value):
    d = _read()
    d[key] = value
    _write(d)
