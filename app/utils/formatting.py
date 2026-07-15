"""Number formatting using the European convention.

``"."`` as thousands separator, ``","`` as decimal separator -- e.g.
``1234.5`` becomes ``"1.234,50"``. Applied everywhere regardless of the
system locale, since the app's users expect this format rather than the
US-style ``1,234.50`` that plain ``f"{value:.2f}"`` produces.
"""

from __future__ import annotations


def format_decimal(value: float, decimals: int = 2) -> str:
    """Format ``value`` with European thousands/decimal separators."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "|").replace(".", ",").replace("|", ".")


def format_price(value: float, currency: str | None = None) -> str:
    """Format ``value`` as a European-style price, optionally with a currency suffix."""
    text = format_decimal(value)
    return f"{text} {currency}" if currency else text
