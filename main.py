"""Interactive expense tracker for the terminal, built on rich."""

import json
import sqlite3
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import storage
from expense import Expense
from reports import filter_by_month, group_by_category, total_amount
from validation import (
    ValidationError,
    parse_amount,
    parse_category,
    parse_date,
    parse_month,
)

console = Console()


# ---------- input helpers ----------

def ask(label: str) -> str:
    """Prompt for one line of input, styled consistently."""
    return console.input(f"[cyan]{label}[/cyan]").strip()


def prompt(parser, label: str):
    """Prompt with `label`, run `parser`, and re-ask until it validates.

    `parser` is one of the parse_* functions from validation.py; this loop is
    the only difference between how the CLI and the web app handle bad input.
    """
    while True:
        try:
            return parser(ask(label))
        except ValidationError as err:
            console.print(f"[red]{err}[/red]")


def read_amount(label: str = "Amount: $") -> float:
    return prompt(parse_amount, label)


def read_date(label: str = "Date (YYYY-MM-DD): ") -> str:
    return prompt(parse_date, label)


def read_month(label: str = "Month (YYYY-MM): ") -> str:
    return prompt(parse_month, label)


def read_category(label: str = "Category (e.g. food, transport, rent): ") -> str:
    return prompt(parse_category, label)


# ---------- display helpers ----------

def expenses_table(expenses: list[Expense]) -> Table:
    """Build a table of expenses, oldest first."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("Date")
    table.add_column("Category")
    table.add_column("Amount", justify="right")
    table.add_column("Note")

    for e in sorted(expenses, key=lambda x: x.date):
        table.add_row(e.id, e.date, e.category, f"${e.amount:.2f}", e.note)
    return table


def find_expense(expenses: list[Expense], expense_id: str) -> Expense | None:
    return next((e for e in expenses if e.id == expense_id), None)


# ---------- menu actions ----------

def add_expense() -> None:
    console.print(Panel("Add Expense", style="bold cyan"))
    expense = Expense(
        amount=read_amount(),
        category=read_category(),
        date=read_date(),
        note=ask("Note (optional): "),
    )
    storage.add_expense(expense)
    console.print("[bold green]Expense added![/bold green]")

    limit = storage.load_budgets().get(expense.category)
    if limit is not None:
        month = expense.date[:7]
        expenses = filter_by_month(storage.load_expenses(), month)
        spent = group_by_category(expenses)[expense.category]
        if spent > limit:
            console.print(
                f"[bold red]Warning: {expense.category} is at ${spent:.2f} for {month}, "
                f"over its ${limit:.2f} monthly budget![/bold red]")
    console.print()


def view_expenses() -> None:
    console.print(Panel("All Expenses", style="bold cyan"))
    expenses = storage.load_expenses()
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    console.print(expenses_table(expenses))
    console.print(f"[bold]Total:[/bold] [green]${total_amount(expenses):.2f}[/green]\n")


def monthly_summary() -> None:
    console.print(Panel("Monthly Summary", style="bold cyan"))
    month = read_month()
    matching = filter_by_month(storage.load_expenses(), month)

    if not matching:
        console.print("[yellow]No expenses found for that month.[/yellow]\n")
        return

    console.print(
        f"[bold]Total spent in {month}:[/bold] "
        f"[green]${total_amount(matching):.2f}[/green]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Category")
    table.add_column("Amount", justify="right")
    for category, amount in group_by_category(matching).items():
        table.add_row(category, f"${amount:.2f}")

    console.print(table)
    console.print()


def edit_expense() -> None:
    console.print(Panel("Edit Expense", style="bold cyan"))
    expenses = storage.load_expenses()
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    console.print(expenses_table(expenses))
    target = find_expense(expenses, ask("Enter the ID to edit: "))
    if target is None:
        console.print("[red]No expense with that ID.[/red]\n")
        return

    console.print("[dim]Press Enter to keep the current value.[/dim]")

    def maybe_update(attr: str, label: str, parser=None) -> None:
        """Ask for a new value; keep the old one on empty or invalid input."""
        raw = ask(label)
        if not raw:
            return
        try:
            setattr(target, attr, parser(raw) if parser else raw)
        except ValidationError as err:
            console.print(f"[red]{err} Keeping the old value.[/red]")

    maybe_update("amount", f"Amount [{target.amount}]: $", parse_amount)
    maybe_update("category", f"Category [{target.category}]: ", parse_category)
    maybe_update("date", f"Date [{target.date}]: ", parse_date)
    maybe_update("note", f"Note [{target.note}]: ")

    storage.update_expense(target)
    console.print("[bold green]Expense updated![/bold green]\n")


def delete_expense() -> None:
    console.print(Panel("Delete Expense", style="bold cyan"))
    expenses = storage.load_expenses()
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    console.print(expenses_table(expenses))
    target = find_expense(expenses, ask("Enter the ID to delete: "))
    if target is None:
        console.print("[red]No expense with that ID.[/red]\n")
        return

    confirm = ask(f"Delete {target.date} | {target.category} | ${target.amount:.2f}? (y/n): ")
    if confirm.lower() == "y":
        storage.delete_expense(target.id)
        console.print("[bold green]Expense deleted.[/bold green]\n")
    else:
        console.print("[yellow]Cancelled.[/yellow]\n")


def manage_budgets() -> None:
    console.print(Panel("Budgets", style="bold cyan"))
    console.print("[cyan]1.[/cyan] Set a budget")
    console.print("[cyan]2.[/cyan] View budget status")
    choice = console.input("[bold]Choose an option: [/bold]").strip()

    if choice == "1":
        category = read_category("Category: ")
        limit = read_amount("Monthly budget: $")
        storage.set_budget(category, limit)
        console.print(f"[bold green]Budget set: {category} -> ${limit:.2f}[/bold green]\n")
    elif choice == "2":
        budgets = storage.load_budgets()
        if not budgets:
            console.print("[yellow]No budgets set yet.[/yellow]\n")
            return

        current_month = datetime.now().strftime("%Y-%m")
        spent = group_by_category(
            filter_by_month(storage.load_expenses(), current_month))
        table = Table(
            title=f"Budget status for {current_month}",
            show_header=True, header_style="bold magenta")
        table.add_column("Category")
        table.add_column("Spent", justify="right")
        table.add_column("Budget", justify="right")
        table.add_column("Status")

        for category, limit in budgets.items():
            amount = spent.get(category, 0.0)
            status = "[red]Over[/red]" if amount > limit else "[green]OK[/green]"
            table.add_row(category, f"${amount:.2f}", f"${limit:.2f}", status)

        console.print(table)
        console.print()
    else:
        console.print("[red]Invalid option.[/red]\n")


def spending_chart() -> None:
    console.print(Panel("Spending by Category", style="bold cyan"))
    expenses = storage.load_expenses()
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    totals = group_by_category(expenses)
    max_amount = max(totals.values())
    bar_width = 40

    for category, amount in sorted(totals.items(), key=lambda item: -item[1]):
        bar = "█" * int((amount / max_amount) * bar_width)
        console.print(f"{category:12} [green]{bar}[/green] ${amount:.2f}")
    console.print()


def export_to_csv() -> None:
    console.print(Panel("Export to CSV", style="bold cyan"))
    expenses = storage.load_expenses()
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    path = storage.export_csv(expenses)
    console.print(f"[bold green]Exported to {path.name}[/bold green]\n")


# ---------- entry point ----------

def main() -> None:
    try:
        storage.load_expenses()  # opens the DB, running first-time migration
    except (json.JSONDecodeError, sqlite3.Error) as err:
        console.print(f"[bold red]Could not open the expense database: {err}[/bold red]")
        return

    actions = {
        "1": ("Add expense", add_expense),
        "2": ("View all expenses", view_expenses),
        "3": ("Monthly summary", monthly_summary),
        "4": ("Edit expense", edit_expense),
        "5": ("Delete expense", delete_expense),
        "6": ("Budgets", manage_budgets),
        "7": ("Spending chart", spending_chart),
        "8": ("Export to CSV", export_to_csv),
    }
    exit_key = "9"

    while True:
        console.print(Panel("[bold]Expense Tracker[/bold]", style="bold blue"))
        for key, (label, _) in actions.items():
            console.print(f"[cyan]{key}.[/cyan] {label}")
        console.print(f"[cyan]{exit_key}.[/cyan] Exit")

        choice = console.input("\n[bold]Choose an option: [/bold]").strip()
        if choice == exit_key:
            console.print("[bold red]Goodbye.[/bold red]")
            break
        if choice in actions:
            actions[choice][1]()
        else:
            console.print("[red]Invalid option, try again.[/red]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Goodbye.[/bold red]")
