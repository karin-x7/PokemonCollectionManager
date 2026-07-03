"""Pokémon Collection Manager application package.

The package is organised into focused sub-packages so that business logic
never lives inside the GUI layer:

- ``config``       — central paths and application constants.
- ``models``       — plain domain objects (dataclasses) and enumerations.
- ``database``     — SQLite connection handling, schema and migrations.
- ``services``     — application/business logic orchestrating the layers.
- ``pricing``      — price discovery engine and provider abstraction.
- ``cardmarket``   — Cardmarket-specific integrations.
- ``recognition``  — card recognition (OCR / image matching).
- ``scanner``      — webcam capture.
- ``export``       — CSV / Excel / JSON / PDF exporters.
- ``ui``           — PySide6 desktop interface.
- ``utils``        — small shared helpers.
"""

from app.config import APP_NAME, APP_VERSION

__all__ = ["APP_NAME", "APP_VERSION"]
