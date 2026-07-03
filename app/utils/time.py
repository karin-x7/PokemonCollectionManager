"""Time helpers.

Timestamps are stored as ISO-8601 UTC strings. Keeping this in one place
guarantees a single, consistent representation across the database.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
