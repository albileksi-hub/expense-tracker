"""Pure calculations over expense lists — no I/O, so everything here is easy to unit test."""

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
