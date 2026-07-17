"""Spending insights: a local analysis that always works, plus an optional
personalized opinion from Claude when an API key is configured.

local_insights() is pure arithmetic — no network, always available (this is what
a Pro account gets even without an API key). ai_opinion() asks Claude to look at
the spending breakdown and suggest where to cut back; it needs ANTHROPIC_API_KEY
and raises InsightsError otherwise, so callers can degrade gracefully.
"""

import os

import anthropic

from reports import group_by_category, total_amount

# Same default as receipt.py — swap for "claude-haiku-4-5" for cheaper calls.
MODEL = "claude-opus-4-8"


class InsightsError(Exception):
    """Raised when an AI opinion can't be generated."""


def local_insights(expenses) -> dict:
    """Summary stats computed locally — biggest category, its share, averages."""
    total = total_amount(expenses)
    breakdown = sorted(group_by_category(expenses).items(), key=lambda kv: -kv[1])

    if not expenses:
        return {"count": 0, "total": 0.0, "average": 0.0,
                "top_category": None, "top_amount": 0.0, "top_share": 0.0,
                "breakdown": []}

    top_category, top_amount = breakdown[0]
    return {
        "count": len(expenses),
        "total": total,
        "average": total / len(expenses),
        "top_category": top_category,
        "top_amount": top_amount,
        "top_share": (top_amount / total) if total else 0.0,
        "breakdown": breakdown,
    }


def is_configured() -> bool:
    """True when an Anthropic API key is available for AI opinions."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def ai_opinion(expenses) -> str:
    """Ask Claude for a short, practical opinion on the user's spending."""
    if not is_configured():
        raise InsightsError(
            "The AI advisor isn't turned on — set the ANTHROPIC_API_KEY "
            "environment variable to enable personalized opinions.")
    if not expenses:
        return "Add a few expenses first, then come back for a personalized opinion."

    breakdown = sorted(group_by_category(expenses).items(), key=lambda kv: -kv[1])
    summary = "\n".join(f"- {category}: ${amount:.2f}" for category, amount in breakdown)
    prompt = (
        f"Here is a person's spending by category (total ${total_amount(expenses):.2f} "
        f"across {len(expenses)} expenses):\n{summary}\n\n"
        "Give a short, friendly, practical opinion in 3-4 bullet points: where they "
        "seem to be overspending or wasting money, and specific, realistic ways to "
        "spend less. Be concrete and encouraging, not preachy. Plain text, no headings."
    )

    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as err:
        raise InsightsError(f"Couldn't reach the AI advisor: {err}")

    return "".join(block.text for block in response.content if block.type == "text").strip()
