from expense import Expense
from reports import (
    filter_by_month,
    group_by_category,
    monthly_totals,
    over_budget_categories,
    total_amount,
)


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


def test_monthly_totals_fills_gaps_and_orders_oldest_first():
    expenses = [
        Expense(100.0, "rent", "2026-05-10"),
        Expense(20.0, "food", "2026-07-02"),
        Expense(30.0, "food", "2026-07-20"),
    ]
    series = monthly_totals(expenses, months=4, anchor="2026-07")

    assert series == [
        ("2026-04", 0.0),   # gap month included as zero
        ("2026-05", 100.0),
        ("2026-06", 0.0),
        ("2026-07", 50.0),  # two July expenses summed
    ]


def test_monthly_totals_crosses_year_boundary():
    series = monthly_totals([Expense(5.0, "food", "2025-12-31")],
                            months=3, anchor="2026-02")
    assert [m for m, _ in series] == ["2025-12", "2026-01", "2026-02"]
    assert series[0][1] == 5.0


def test_monthly_totals_empty():
    series = monthly_totals([], months=3, anchor="2026-07")
    assert series == [("2026-05", 0.0), ("2026-06", 0.0), ("2026-07", 0.0)]
