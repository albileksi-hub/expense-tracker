"""The Expense model: one record of money spent."""

import uuid
from dataclasses import dataclass, field
from typing import Any


def _new_id() -> str:
    """Short random id, easy to type when editing or deleting."""
    return uuid.uuid4().hex[:8]


@dataclass
class Expense:
    """A single expense entry."""

    amount: float
    category: str
    date: str  # ISO format: YYYY-MM-DD
    note: str = ""
    id: str = field(default_factory=_new_id)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dict so it can be stored as JSON."""
        return {
            "id": self.id,
            "amount": self.amount,
            "category": self.category,
            "date": self.date,
            "note": self.note,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Expense":
        """Rebuild an Expense from a dict loaded from JSON."""
        return Expense(
            amount=data["amount"],
            category=data["category"],
            date=data["date"],
            note=data.get("note", ""),
            id=data.get("id") or _new_id(),
        )
