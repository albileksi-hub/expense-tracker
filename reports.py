"""Pure data-crunching helpers, kept separate from I/O so they're easy to test."""


def filter_by_month(expenses, month):
    """month is a 'YYYY-MM' string."""
    return [e for e in expenses if e.date.startswith(month)]


def total_amount(expenses):
    return sum(e.amount for e in expenses)


def group_by_category(expenses):
    totals = {}
    for e in expenses:
        totals[e.category] = totals.get(e.category, 0) + e.amount
    return totals


def over_budget_categories(expenses, budgets):
    """Returns {category: (spent, budget)} for categories that exceed their budget."""
    spent = group_by_category(expenses)
    return {
        category: (spent[category], limit)
        for category, limit in budgets.items()
        if spent.get(category, 0) > limit
    }
