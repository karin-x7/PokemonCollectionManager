"""Checks GitHub Releases for a newer version than the one currently running.

Purely a courtesy "a new version is available" hint in the status bar (see
``app.ui.workers.update_check_worker``) -- there's no auto-download/install,
just a link to the release page. Best-effort only: any failure (no internet,
GitHub rate limit, an unexpected response shape) is treated exactly like "no
newer version found", never surfaced as an error.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from app.logging_config import get_logger

logger = get_logger(__name__)

_RELEASES_URL = "https://api.github.com/repos/{repo}/releases/latest"
_DEFAULT_REPO = "codeonEXE/PokemonCollectionManager"
_TIMEOUT = 5.0


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    url: str


def _version_key(text: str) -> tuple:
    """A tuple key for comparing version strings (best-effort semver-lite).

    ``"0.9.0"`` sorts higher than any prerelease of the same release (e.g.
    ``"0.9.0-alpha.1"``), matching normal semver precedence.
    """
    release_part, _, prerelease_part = text.strip().lstrip("vV").partition("-")
    release = tuple(int(p) if p.isdigit() else 0 for p in release_part.split("."))
    if not prerelease_part:
        return (release, (1,))
    prerelease = tuple(int(p) if p.isdigit() else p for p in prerelease_part.split("."))
    return (release, (0, prerelease))


def check_for_update(current_version: str, repo: str = _DEFAULT_REPO) -> UpdateInfo | None:
    """The latest GitHub release, if it's newer than ``current_version``, else ``None``.

    Never raises -- see module docstring.
    """
    try:
        response = requests.get(
            _RELEASES_URL.format(repo=repo),
            headers={"Accept": "application/vnd.github+json"},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        tag = str(payload["tag_name"]).lstrip("vV")
        html_url = str(payload["html_url"])
        is_newer = _version_key(tag) > _version_key(current_version)
    except Exception:  # noqa: BLE001 — best-effort, see module docstring
        logger.info("Update check failed or found nothing usable", exc_info=True)
        return None

    return UpdateInfo(version=tag, url=html_url) if is_newer else None
