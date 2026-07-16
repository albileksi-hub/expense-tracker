"""Interactive expense tracker for the terminal, built on rich."""

import json
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from expense import Expense
from reports import filter_by_month, group_by_category, total_amount
from storage import (
    export_csv,
    load_budgets,
    load_expenses,
    save_budgets,
    save_expenses,
)

console = Console()


# ---------- input helpers ----------

def ask(label: str) -> str:
    """Prompt for one line of input, styled consistently."""
    return console.input(f"[cyan]{label}[/cyan]").strip()


def read_amount(label: str = "Amount: $") -> float:
    """Prompt until the user types a positive number."""
    while True:
        raw = ask(label)
        try:
            amount = float(raw)
        except ValueError:
            console.print("[red]That's not a valid number, try again.[/red]")
            continue
        if amount <= 0:
            console.print("[red]Amount must be greater than zero.[/red]")
            continue
        return amount


def read_date(label: str = "Date (YYYY-MM-DD): ") -> str:
    """Prompt until the user types a real calendar date."""
    while True:
        raw = ask(label)
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
        except ValueError:
            console.print("[red]Please enter a real date in YYYY-MM-DD format.[/red]")


def read_month(label: str = "Month (YYYY-MM): ") -> str:
    """Prompt until the user types a valid year-month."""
    while True:
        raw = ask(label)
        try:
            return datetime.strptime(raw, "%Y-%m").strftime("%Y-%m")
        except ValueError:
            console.print("[red]Please use YYYY-MM format, e.g. 2026-07.[/red]")


def read_category(label: str = "Category (e.g. food, transport, rent): ") -> str:
    """Prompt until the user types a non-empty category; normalized to lowercase."""
    while True:
        category = ask(label).lower()
        if category:
            return category
        console.print("[red]Category can't be empty.[/red]")


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

def add_expense(expenses: list[Expense], budgets: dict[str, float]) -> None:
    console.print(Panel("Add Expense", style="bold cyan"))
    expense = Expense(
        amount=read_amount(),
        category=read_category(),
        date=read_date(),
        note=ask("Note (optional): "),
    )
    expenses.append(expense)
    save_expenses(expenses)
    console.print("[bold green]Expense added![/bold green]")

    limit = budgets.get(expense.category)
    if limit is not None:
        month = expense.date[:7]
        spent = group_by_category(filter_by_month(expenses, month))[expense.category]
        if spent > limit:
            console.print(
                f"[bold red]Warning: {expense.category} is at ${spent:.2f} for {month}, "
                f"over its ${limit:.2f} monthly budget![/bold red]")
    console.print()


def view_expenses(expenses: list[Expense]) -> None:
    console.print(Panel("All Expenses", style="bold cyan"))
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    console.print(expenses_table(expenses))
    console.print(f"[bold]Total:[/bold] [green]${total_amount(expenses):.2f}[/green]\n")


def monthly_summary(expenses: list[Expense]) -> None:
    console.print(Panel("Monthly Summary", style="bold cyan"))
    month = read_month()
    matching = filter_by_month(expenses, month)

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


def edit_expense(expenses: list[Expense]) -> None:
    console.print(Panel("Edit Expense", style="bold cyan"))
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    console.print(expenses_table(expenses))
    target = find_expense(expenses, ask("Enter the ID to edit: "))
    if target is None:
        console.print("[red]No expense with that ID.[/red]\n")
        return

    console.print("[dim]Press Enter to keep the current value.[/dim]")

    raw = ask(f"Amount [{target.amount}]: $")
    if raw:
        try:
            target.amount = float(raw)
        except ValueError:
            console.print("[red]Invalid amount, keeping the old value.[/red]")

    raw = ask(f"Category [{target.category}]: ")
    if raw:
        target.category = raw.lower()

    raw = ask(f"Date [{target.date}]: ")
    if raw:
        try:
            target.date = datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
        except ValueError:
            console.print("[red]Invalid date, keeping the old value.[/red]")

    raw = ask(f"Note [{target.note}]: ")
    if raw:
        target.note = raw

    save_expenses(expenses)
    console.print("[bold green]Expense updated![/bold green]\n")


def delete_expense(expenses: list[Expense]) -> None:
    console.print(Panel("Delete Expense", style="bold cyan"))
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
        expenses.remove(target)
        save_expenses(expenses)
        console.print("[bold green]Expense deleted.[/bold green]\n")
    else:
        console.print("[yellow]Cancelled.[/yellow]\n")


def manage_budgets(expenses: list[Expense], budgets: dict[str, float]) -> None:
    console.print(Panel("Budgets", style="bold cyan"))
    console.print("[cyan]1.[/cyan] Set a budget")
    console.print("[cyan]2.[/cyan] View budget status")
    choice = console.input("[bold]Choose an option: [/bold]").strip()

    if choice == "1":
        category = read_category("Category: ")
        limit = read_amount("Monthly budget: $")
        budgets[category] = limit
        save_budgets(budgets)
        console.print(f"[bold green]Budget set: {category} -> ${limit:.2f}[/bold green]\n")
    elif choice == "2":
        if not budgets:
            console.print("[yellow]No budgets set yet.[/yellow]\n")
            return

        current_month = datetime.now().strftime("%Y-%m")
        spent = group_by_category(filter_by_month(expenses, current_month))
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


def spending_chart(expenses: list[Expense]) -> None:
    console.print(Panel("Spending by Category", style="bold cyan"))
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


def export_to_csv(expenses: list[Expense]) -> None:
    console.print(Panel("Export to CSV", style="bold cyan"))
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    path = export_csv(expenses)
    console.print(f"[bold green]Exported to {path.name}[/bold green]\n")


# ---------- entry point ----------

def main() -> None:
    try:
        expenses = load_expenses()
        budgets = load_budgets()
    except json.JSONDecodeError as err:
        console.print(
            "[bold red]Could not read saved data — "
            f"data.json or budgets.json is not valid JSON ({err}).[/bold red]")
        return

    actions = {
        "1": ("Add expense", lambda: add_expense(expenses, budgets)),
        "2": ("View all expenses", lambda: view_expenses(expenses)),
        "3": ("Monthly summary", lambda: monthly_summary(expenses)),
        "4": ("Edit expense", lambda: edit_expense(expenses)),
        "5": ("Delete expense", lambda: delete_expense(expenses)),
        "6": ("Budgets", lambda: manage_budgets(expenses, budgets)),
        "7": ("Spending chart", lambda: spending_chart(expenses)),
        "8": ("Export to CSV", lambda: export_to_csv(expenses)),
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
