import pytest

import insights
from expense import Expense


def make_expenses():
    return [
        Expense(100.0, "rent", "2026-07-01"),
        Expense(30.0, "food", "2026-07-02"),
        Expense(20.0, "food", "2026-07-03"),
        Expense(50.0, "shoes", "2026-07-04"),
    ]


def test_local_insights_empty():
    result = insights.local_insights([])
    assert result["count"] == 0
    assert result["top_category"] is None
    assert result["breakdown"] == []


def test_local_insights_math():
    result = insights.local_insights(make_expenses())

    assert result["count"] == 4
    assert result["total"] == 200.0
    assert result["average"] == 50.0
    assert result["top_category"] == "rent"
    assert result["top_amount"] == 100.0
    assert result["top_share"] == 0.5  # rent is half of all spending
    # breakdown is sorted high to low
    assert result["breakdown"][0] == ("rent", 100.0)


def test_ai_opinion_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert insights.is_configured() is False
    with pytest.raises(insights.InsightsError):
        insights.ai_opinion(make_expenses())
