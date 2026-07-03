"""Central application configuration: constants and filesystem paths.

All paths are derived from the project root so the application is fully
self-contained and stores its data locally, as required. Individual paths
can be overridden through environment variables, which keeps the layout
flexible for tests and multi-machine synchronisation.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME: str = "Pokémon Collection Manager"
APP_VERSION: str = "0.1.0"

# Project root = parent directory of the ``app`` package.
BASE_DIR: Path = Path(__file__).resolve().parent.parent


def _path_from_env(env_var: str, default: Path) -> Path:
    """Return the path from ``env_var`` if set, otherwise ``default``."""
    value = os.environ.get(env_var)
    return Path(value).expanduser().resolve() if value else default


DATA_DIR: Path = _path_from_env("PCM_DATA_DIR", BASE_DIR / "data")
LOGS_DIR: Path = _path_from_env("PCM_LOGS_DIR", BASE_DIR / "logs")
PHOTOS_DIR: Path = DATA_DIR / "photos"

DB_PATH: Path = _path_from_env("PCM_DB_PATH", DATA_DIR / "collection.db")
LOG_FILE: Path = LOGS_DIR / "application.log"

#: Default fiat currency used for prices (Cardmarket trades in EUR).
DEFAULT_CURRENCY: str = "EUR"


def ensure_directories() -> None:
    """Create the data, photos and logs directories if they do not exist."""
    for directory in (DATA_DIR, PHOTOS_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
