"""Loading of local, non-versioned credentials (API tokens/keys).

Secrets live in ``config/secrets.json``, which is git-ignored and never leaves
the local machine. Reading is defensive: a missing file or key yields the
supplied default instead of raising, so the application starts fine before any
provider has been configured. Secret *values* are never written to the log.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app import config
from app.logging_config import get_logger

logger = get_logger(__name__)


def _secrets_path() -> Path:
    """Location of the secrets file (overridable via ``PCM_SECRETS_PATH``)."""
    override = os.environ.get("PCM_SECRETS_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return config.BASE_DIR / "config" / "secrets.json"


def load_secrets() -> dict[str, Any]:
    """Return the parsed secrets file, or an empty dict if absent/invalid."""
    path = _secrets_path()
    if not path.exists():
        logger.info("No secrets file at %s — running without credentials.", path)
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Could not read secrets file %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.error("Secrets file %s must contain a JSON object.", path)
        return {}
    return data


def get_secret(*keys: str, default: Any = None) -> Any:
    """Return a nested secret value, e.g. ``get_secret("cardtrader", "jwt_token")``.

    Empty strings and ``None`` are treated as "not set" and return ``default``.
    """
    data: Any = load_secrets()
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return default if data in (None, "") else data


def has_cardtrader_token() -> bool:
    """Whether a non-empty CardTrader JWT is configured."""
    return get_secret("cardtrader", "jwt_token") is not None
