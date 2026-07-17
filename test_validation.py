import pytest

from validation import (
    ValidationError,
    parse_amount,
    parse_category,
    parse_date,
    parse_month,
)


def test_parse_amount_accepts_positive_numbers():
    assert parse_amount("12.50") == 12.5
    assert parse_amount("3") == 3.0


@pytest.mark.parametrize("bad", ["", "abc", None, "0", "-5"])
def test_parse_amount_rejects_bad_values(bad):
    with pytest.raises(ValidationError):
        parse_amount(bad)


def test_parse_date_canonicalizes():
    assert parse_date("  2026-07-17  ") == "2026-07-17"


@pytest.mark.parametrize("bad", ["", "2026-13-99", "17/07/2026", "not-a-date"])
def test_parse_date_rejects_bad_values(bad):
    with pytest.raises(ValidationError):
        parse_date(bad)


def test_parse_month_canonicalizes():
    assert parse_month("2026-07") == "2026-07"


@pytest.mark.parametrize("bad", ["", "2026", "2026-13", "July"])
def test_parse_month_rejects_bad_values(bad):
    with pytest.raises(ValidationError):
        parse_month(bad)


def test_parse_category_normalizes_case_and_whitespace():
    assert parse_category("  Food  ") == "food"


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_parse_category_rejects_empty(bad):
    with pytest.raises(ValidationError):
        parse_category(bad)
