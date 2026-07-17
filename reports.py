"""Pure calculations over expense lists — no I/O, so everything here is easy to unit test."""

from datetime import date

from expense import Expense


def filter_by_month(expenses: list[Expense], month: str) -> list[Expense]:
    """Keep only expenses whose date falls in the given 'YYYY-MM' month."""
    return [e for e in expenses if e.date.startswith(month)]


def total_amount(expenses: list[Expense]) -> float:
    """Sum of all expense amounts."""
    return sum(e.amount for e in expenses)


def group_by_category(expenses: list[Expense]) -> dict[str, float]:
    """Total spent per category."""
    totals: dict[str, float] = {}
    for e in expenses:
        totals[e.category] = totals.get(e.category, 0.0) + e.amount
    return totals


def over_budget_categories(
    expenses: list[Expense], budgets: dict[str, float]
) -> dict[str, tuple[float, float]]:
    """Categories spending past their budget, as {category: (spent, budget)}."""
    spent = group_by_category(expenses)
    return {
        category: (spent[category], limit)
        for category, limit in budgets.items()
        if spent.get(category, 0.0) > limit
    }


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Move `delta` months from (year, month), handling year boundaries."""
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def monthly_totals(
    expenses: list[Expense], months: int = 6, anchor: str | None = None
) -> list[tuple[str, float]]:
    """Total spent in each of the last `months` months, oldest first.

    Each item is ('YYYY-MM', total); months with no spending are included as 0.0
    so the trend line is continuous. `anchor` ('YYYY-MM') sets the most recent
    month shown; it defaults to whichever is later — this month or the latest
    expense — so future-dated demo data still appears.
    """
    totals: dict[str, float] = {}
    for e in expenses:
        key = e.date[:7]
        totals[key] = totals.get(key, 0.0) + e.amount

    today = date.today()
    this_month = f"{today.year:04d}-{today.month:02d}"
    anchor = anchor or max([*totals.keys(), this_month])
    anchor_year, anchor_month = int(anchor[:4]), int(anchor[5:7])

    series = []
    for offset in range(months - 1, -1, -1):
        year, month = _shift_month(anchor_year, anchor_month, -offset)
        key = f"{year:04d}-{month:02d}"
        series.append((key, totals.get(key, 0.0)))
    return series
