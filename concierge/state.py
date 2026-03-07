"""Atomic session-state persistence (YAML).

Provides helpers to save and load :class:`~concierge.models.SessionState`
to/from a YAML file on disk.  Writes are atomic: the data is first flushed
to a temporary file in the same directory, then renamed into place so that
a crash mid-write never leaves a corrupt file behind.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from concierge.models import FeatureType, MessageClass, SessionState, Suite


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _enum_to_str(val: MessageClass | Suite | FeatureType | None) -> str | None:
    """Return the enum's *value* string, or ``None``."""
    return val.value if val is not None else None


def _datetime_to_str(val: datetime | None) -> str | None:
    """Return an ISO-8601 string, or ``None``."""
    return val.isoformat() if val is not None else None


def _str_to_datetime(val: str | None) -> datetime | None:
    """Parse an ISO-8601 string back to a :class:`datetime`, or ``None``."""
    if val is None:
        return None
    return datetime.fromisoformat(val)


def _session_state_to_dict(state: SessionState) -> dict:
    """Convert a :class:`SessionState` to a plain dict suitable for YAML."""
    return {
        "current_suite": _enum_to_str(state.current_suite),
        "suite_since": _datetime_to_str(state.suite_since),
        "active_feature": _enum_to_str(state.active_feature),
        "active_feature_id": state.active_feature_id,
        "feature_started_at": _datetime_to_str(state.feature_started_at),
        "recent_classifications": [c.value for c in state.recent_classifications],
        "recent_suites": [s.value for s in state.recent_suites],
        "last_message_at": _datetime_to_str(state.last_message_at),
        "processing_cooldown_remaining": state.processing_cooldown_remaining,
    }


def _dict_to_session_state(data: dict) -> SessionState:
    """Reconstruct a :class:`SessionState` from a plain dict."""
    return SessionState(
        current_suite=(
            Suite(data["current_suite"]) if data.get("current_suite") else None
        ),
        suite_since=_str_to_datetime(data.get("suite_since")),
        active_feature=(
            FeatureType(data["active_feature"])
            if data.get("active_feature")
            else None
        ),
        active_feature_id=data.get("active_feature_id"),
        feature_started_at=_str_to_datetime(data.get("feature_started_at")),
        recent_classifications=[
            MessageClass(v) for v in (data.get("recent_classifications") or [])
        ],
        recent_suites=[Suite(v) for v in (data.get("recent_suites") or [])],
        last_message_at=_str_to_datetime(data.get("last_message_at")),
        processing_cooldown_remaining=data.get(
            "processing_cooldown_remaining", 0
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_session_state(state: SessionState, path: Path) -> None:
    """Atomically write *state* to *path* as YAML.

    The file is first written to a temporary file in the same directory, then
    moved into place via :func:`os.rename` so that readers always see either
    the old or the new version — never a partially-written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = _session_state_to_dict(state)

    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, suffix=".tmp", prefix=".session_"
    )
    try:
        with os.fdopen(fd, "w") as fh:
            yaml.safe_dump(data, fh, default_flow_style=False)
        os.rename(tmp_path, path)
    except BaseException:
        # Clean up the temp file on any failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_session_state(path: Path) -> SessionState:
    """Load a :class:`SessionState` from *path*.

    Returns a default (empty) :class:`SessionState` if *path* does not exist.
    """
    path = Path(path)
    if not path.exists():
        return SessionState()

    with open(path) as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        return SessionState()

    return _dict_to_session_state(data)
