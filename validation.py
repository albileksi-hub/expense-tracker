"""Input validation shared by both front ends (CLI and web).

Each `parse_*` function takes raw user input and returns a clean, canonical
value, or raises ValidationError with a human-readable message. Keeping these
rules in one place means the terminal app and the web app accept exactly the
same input and reject the same bad input — no drift between the two.
"""

from datetime import datetime


class ValidationError(ValueError):
    """Raised when user input fails a validation rule."""


def parse_amount(raw: str) -> float:
    """Return a positive float, or raise ValidationError."""
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        raise ValidationError("Amount must be a number.")
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.")
    return amount


def parse_date(raw: str) -> str:
    """Return a canonical 'YYYY-MM-DD' date string, or raise ValidationError."""
    try:
        return datetime.strptime((raw or "").strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValidationError("Date must be a real date in YYYY-MM-DD format.")


def parse_month(raw: str) -> str:
    """Return a canonical 'YYYY-MM' month string, or raise ValidationError."""
    try:
        return datetime.strptime((raw or "").strip(), "%Y-%m").strftime("%Y-%m")
    except ValueError:
        raise ValidationError("Month must be in YYYY-MM format, e.g. 2026-07.")


def parse_category(raw: str) -> str:
    """Return a non-empty, lower-cased, trimmed category, or raise ValidationError."""
    category = (raw or "").strip().lower()
    if not category:
        raise ValidationError("Category can't be empty.")
    return category
