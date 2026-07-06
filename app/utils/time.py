"""Time helpers.

Timestamps are stored as ISO-8601 UTC strings. Keeping this in one place
guarantees a single, consistent representation across the database.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


#: Extra spacing between the date and time portions of a formatted
#: timestamp -- a single plain space made them look too tight together
#: (user feedback), especially at the small font sizes these appear at.
_DATE_TIME_GAP = "   "


def format_display_datetime(iso: str) -> str:
    """Format a stored ISO-8601 timestamp for display: ``"dd.MM.yyyy   HH:mm"``."""
    return datetime.fromisoformat(iso).strftime(f"%d.%m.%Y{_DATE_TIME_GAP}%H:%M")
