"""Central rotating logger for FiberHome Manager.

Wraps Python's stdlib `logging` so the app, all workers, and any third-
party code that bubbles up exceptions write to a single rotating file:

    %USERPROFILE%/.fiberguard/logs/app.log     (current)
    %USERPROFILE%/.fiberguard/logs/app.log.1
    %USERPROFILE%/.fiberguard/logs/app.log.2
    ...

Why stdlib `logging` and not a custom hook? Because anti-cheat software
(BattlEye, EAC, VAC, Vanguard, Ricochet) flags processes that:

    - inject DLLs into other processes
    - hook the win32 API
    - read another process's memory
    - install global keyboard / mouse hooks

`logging.handlers.RotatingFileHandler` does NONE of those — it just
opens a file handle in the user's home directory and calls write() on
it. Same as Notepad. Safe in every gaming environment we know of.
"""
import logging
import logging.handlers
import os
import sys
import platform
import time
import traceback
from pathlib import Path


# ───── Paths ─────
LOG_DIR  = Path.home() / ".fiberguard" / "logs"
LOG_FILE = LOG_DIR / "app.log"

_LOG_FORMAT = ("%(asctime)s.%(msecs)03d  [%(levelname)-5s]  %(name)-14s  "
                "%(message)s")
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Module-level handle so we can re-target on restart.
_logger      = None
_initialised = False


def init(level: str = "INFO", max_bytes: int = 1_048_576,
          backup_count: int = 5):
    """Idempotent. Sets up a rotating file logger + console mirror."""
    global _logger, _initialised
    if _initialised:
        return _logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("fiberguard")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Don't double-log via the parent root logger.
    root.propagate = False
    # Wipe any previous handlers — happens during dev re-imports.
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Rotating file handler (5 × 1MB by default)
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=max_bytes, backupCount=backup_count,
        encoding="utf-8", delay=True)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Mirror to stderr only when running from source (not from frozen exe).
    if not getattr(sys, "frozen", False):
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fmt)
        root.addHandler(sh)

    _logger = root
    _initialised = True

    # Boot banner makes it obvious in the file where each session starts.
    root.info("─" * 78)
    root.info(f"FiberHome Manager — session start ({time.strftime('%c')})")
    root.info(f"Python {sys.version.split()[0]} · "
                f"{platform.system()} {platform.release()} ({platform.machine()})")
    root.info(f"Frozen: {bool(getattr(sys, 'frozen', False))} · "
                f"Log dir: {LOG_DIR}")
    return root


def get(name: str = "app") -> logging.Logger:
    """Get a child logger; auto-init if init() hasn't been called yet."""
    if not _initialised:
        init()
    return logging.getLogger(f"fiberguard.{name}")


# ───── Convenience top-level functions ─────
def info   (msg: str, name: str = "app"): get(name).info(msg)
def warn   (msg: str, name: str = "app"): get(name).warning(msg)
def error  (msg: str, name: str = "app"): get(name).error(msg)
def debug  (msg: str, name: str = "app"): get(name).debug(msg)
def exc    (msg: str, name: str = "app"): get(name).exception(msg)


# ───── Global crash handler ─────
def install_excepthook():
    """Catch any unhandled Python exception and dump it to the log.
    Without this, a crash in a Qt slot just disappears."""
    if not _initialised:
        init()

    prev_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        try:
            tb_text = "".join(traceback.format_exception(
                exc_type, exc_value, exc_tb))
            get("crash").critical(f"Unhandled exception:\n{tb_text}")
        except Exception:
            pass
        # Chain to the previous handler so the IDE/console still sees it.
        try: prev_hook(exc_type, exc_value, exc_tb)
        except Exception: pass

    sys.excepthook = _hook


def shutdown_banner():
    """Write the closing line so log readers see clean session boundaries."""
    if _initialised and _logger is not None:
        try:
            _logger.info(f"Session end ({time.strftime('%c')})")
            _logger.info("─" * 78)
        except Exception: pass


# ───── User-friendly helpers ─────
def open_log_folder():
    """Open the log directory in the OS file explorer."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(LOG_DIR)
        elif sys.platform == "darwin":
            import subprocess; subprocess.Popen(["open", str(LOG_DIR)])
        else:
            import subprocess; subprocess.Popen(["xdg-open", str(LOG_DIR)])
        return True
    except Exception as e:
        get("log").error(f"Failed to open log folder: {e}")
        return False


def clear_logs():
    """Delete every rotated log file. Returns count of deleted files."""
    count = 0
    if not LOG_DIR.is_dir(): return 0
    for p in LOG_DIR.glob("app.log*"):
        try: p.unlink(); count += 1
        except Exception: pass
    return count
