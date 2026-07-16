from expense import Expense
from reports import filter_by_month, total_amount, group_by_category, over_budget_categories


def make_expenses():
    return [
        Expense(12.0, "food", "2026-06-02", "lunch"),
        Expense(50.0, "food", "2026-06-15", "groceries"),
        Expense(200.0, "shoes", "2026-07-16", "trainers"),
    ]


def test_expense_round_trips_through_dict():
    e = Expense(9.5, "transport", "2026-07-01", "bus")
    rebuilt = Expense.from_dict(e.to_dict())

    assert rebuilt == e


def test_from_dict_fills_in_defaults():
    e = Expense.from_dict({"amount": 5.0, "category": "food", "date": "2026-01-01"})

    assert e.note == ""
    assert e.id  # an id gets generated when the stored data has none


def test_filter_by_month():
    expenses = make_expenses()
    june = filter_by_month(expenses, "2026-06")

    assert len(june) == 2
    assert all(e.date.startswith("2026-06") for e in june)


def test_total_amount():
    assert total_amount(make_expenses()) == 262.0
    assert total_amount([]) == 0


def test_group_by_category():
    totals = group_by_category(make_expenses())

    assert totals == {"food": 62.0, "shoes": 200.0}


def test_over_budget_categories():
    expenses = make_expenses()
    budgets = {"food": 100.0, "shoes": 100.0}

    over = over_budget_categories(expenses, budgets)

    assert list(over.keys()) == ["shoes"]
    assert over["shoes"] == (200.0, 100.0)
