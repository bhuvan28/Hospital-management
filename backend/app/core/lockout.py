from __future__ import annotations

import threading
import time

# In-memory lockout for a single backend process. Failed attempts are keyed by
# email (lowercased) so unknown addresses are treated the same as known ones.
_lock = threading.Lock()
_failures: dict[str, list[float]] = {}
_locked_until: dict[str, float] = {}

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60
LOCK_SECONDS = 15 * 60


def reset_lockout() -> None:
    with _lock:
        _failures.clear()
        _locked_until.clear()


def _prune(key: str, now: float) -> None:
    stamps = [stamp for stamp in _failures.get(key, []) if now - stamp <= WINDOW_SECONDS]
    if stamps:
        _failures[key] = stamps
    else:
        _failures.pop(key, None)
    until = _locked_until.get(key)
    if until is not None and until <= now:
        _locked_until.pop(key, None)


def is_locked(email: str) -> bool:
    key = email.strip().lower()
    now = time.time()
    with _lock:
        _prune(key, now)
        until = _locked_until.get(key)
        return until is not None and until > now


def record_failure(email: str) -> bool:
    """Record a failed login. Returns True if the address is now locked."""
    key = email.strip().lower()
    now = time.time()
    with _lock:
        _prune(key, now)
        stamps = _failures.setdefault(key, [])
        stamps.append(now)
        if len(stamps) >= MAX_FAILURES:
            _locked_until[key] = now + LOCK_SECONDS
            _failures.pop(key, None)
            return True
        return key in _locked_until and _locked_until[key] > now


def clear_failures(email: str) -> None:
    key = email.strip().lower()
    with _lock:
        _failures.pop(key, None)
        _locked_until.pop(key, None)
