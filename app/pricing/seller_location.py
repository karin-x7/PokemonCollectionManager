"""Global seller-location preference for automatic price lookups.

Off (the default) means Europe-wide, i.e. no ``sellerCountry`` filter at
all -- unchanged from the app's original behaviour. Currently only "Germany"
is offered as the alternative (the only country id confirmed live so far,
see :data:`~app.pricing.cardmarket_parsing.SELLER_COUNTRY_GERMANY_ID`); more
countries can be added later without changing this module's shape, just the
setting's possible values.
"""

from __future__ import annotations

from app.database.repositories.settings_repository import SettingsRepository
from app.pricing.cardmarket_parsing import SELLER_COUNTRY_GERMANY_ID

#: Key into the generic ``settings`` key/value table (see
#: ``SettingsRepository``). ``"1"`` means Germany-only; unset or any other
#: value means off (Europe-wide).
_SETTINGS_KEY = "seller_location_germany_only"


def is_germany_only_enabled(settings: SettingsRepository) -> bool:
    """Whether the user has restricted automatic price lookups to German sellers."""
    return settings.get(_SETTINGS_KEY, "0") == "1"


def set_germany_only_enabled(settings: SettingsRepository, enabled: bool) -> None:
    """Persist the Germany-only seller-location preference."""
    settings.set(_SETTINGS_KEY, "1" if enabled else "0")


def resolve_seller_country_id(settings: SettingsRepository | None) -> int | None:
    """The Cardmarket ``sellerCountry`` id to prefer, or ``None`` for no filter.

    ``settings=None`` (e.g. a ``PriceService`` constructed without one, such
    as in tests) always resolves to ``None`` -- no seller-location filtering
    at all, the same as the setting being off.
    """
    if settings is None:
        return None
    return SELLER_COUNTRY_GERMANY_ID if is_germany_only_enabled(settings) else None
