import uuid


class Expense:
    """Represents a single expense entry."""

    def __init__(self, amount, category, date, note="", expense_id=None):
        self.id = expense_id or uuid.uuid4().hex[:8]
        self.amount = amount
        self.category = category
        self.date = date
        self.note = note

    def to_dict(self):
        """Convert this expense into a dictionary, so it can be saved as JSON."""
        return {
            "id": self.id,
            "amount": self.amount,
            "category": self.category,
            "date": self.date,
            "note": self.note
        }

    @staticmethod
    def from_dict(data):
        """Create an Expense object back from a dictionary (used when loading from JSON)."""
        return Expense(
            amount=data["amount"],
            category=data["category"],
            date=data["date"],
            note=data.get("note", ""),
            expense_id=data.get("id")
        )

    def __str__(self):
        """Defines how an Expense prints when we do print(expense)."""
        return f"{self.date} | {self.category:12} | ${self.amount:.2f} | {self.note}"
