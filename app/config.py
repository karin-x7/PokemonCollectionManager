"""Central application configuration: constants and filesystem paths.

All paths are derived from the project root so the application is fully
self-contained and stores its data locally, as required. Individual paths
can be overridden through environment variables, which keeps the layout
flexible for tests and multi-machine synchronisation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME: str = "Pokémon Collection Manager"
APP_VERSION: str = "0.10.0-alpha.1"

if getattr(sys, "frozen", False):
    # Running as a PyInstaller-built .exe: __file__ would resolve inside the
    # temporary extraction directory (sys._MEIPASS), which PyInstaller wipes
    # after the process exits -- using it here would silently lose the
    # database, photos and logs on every restart. The .exe's own directory
    # is stable across launches, so data lives next to it instead.
    BASE_DIR: Path = Path(sys.executable).resolve().parent
    # data/ and logs/ live inside their own named subfolder rather than
    # directly beside the .exe (user request): if someone runs the .exe
    # straight from their Desktop, two loose "data"/"logs" folders would
    # otherwise clutter it -- one clearly-named folder is less messy.
    _APP_DATA_ROOT: Path = BASE_DIR / "PokemonCollectionManager"
else:
    # Project root = parent directory of the ``app`` package. Unaffected by
    # the .exe case above: a source checkout already keeps data/ and logs/
    # at the project root, and nothing about that is "loose on the Desktop".
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    _APP_DATA_ROOT: Path = BASE_DIR


def _path_from_env(env_var: str, default: Path) -> Path:
    """Return the path from ``env_var`` if set, otherwise ``default``."""
    value = os.environ.get(env_var)
    return Path(value).expanduser().resolve() if value else default


DATA_DIR: Path = _path_from_env("PCM_DATA_DIR", _APP_DATA_ROOT / "data")
LOGS_DIR: Path = _path_from_env("PCM_LOGS_DIR", _APP_DATA_ROOT / "logs")
PHOTOS_DIR: Path = DATA_DIR / "photos"
#: Sealed products' own photos (screenshot-captured from Cardmarket, unlike
#: cards' pokemontcg.io downloads) -- kept in a separate directory rather
#: than mixed into PHOTOS_DIR so the two capture mechanisms/lifecycles stay
#: distinguishable on disk.
SEALED_PHOTOS_DIR: Path = DATA_DIR / "sealed_photos"
SET_ICONS_DIR: Path = DATA_DIR / "set_icons"
#: Timestamped copies of the database file, made automatically before schema
#: migrations run -- see ``app.database.backup``. Kept outside DATA_DIR's
#: other subfolders so a backup restore is a plain "copy this one file back",
#: not tangled up with photos/icons.
BACKUPS_DIR: Path = DATA_DIR / "backups"

DB_PATH: Path = _path_from_env("PCM_DB_PATH", DATA_DIR / "collection.db")
LOG_FILE: Path = LOGS_DIR / "application.log"

#: Default fiat currency used for prices (Cardmarket trades in EUR).
DEFAULT_CURRENCY: str = "EUR"


def ensure_directories() -> None:
    """Create the data, photos and logs directories if they do not exist."""
    for directory in (
        DATA_DIR,
        PHOTOS_DIR,
        SEALED_PHOTOS_DIR,
        SET_ICONS_DIR,
        BACKUPS_DIR,
        LOGS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
