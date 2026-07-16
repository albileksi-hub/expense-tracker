import csv

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from expense import Expense
from storage import save_expenses, load_expenses, save_budgets, load_budgets
from reports import filter_by_month, total_amount, group_by_category, over_budget_categories

console = Console()

CSV_FILE = "expenses.csv"


def read_amount(prompt="[cyan]Amount: $[/cyan]"):
    """Keep asking until the user types a valid positive number."""
    while True:
        raw = console.input(prompt)
        try:
            amount = float(raw)
            if amount <= 0:
                console.print("[red]Amount must be greater than zero.[/red]")
                continue
            return amount
        except ValueError:
            console.print("[red]That's not a valid number, try again.[/red]")


def find_expense(expenses, expense_id):
    for e in expenses:
        if e.id == expense_id:
            return e
    return None


def add_expense(expenses, budgets):
    console.print(Panel("Add Expense", style="bold cyan"))
    amount = read_amount()
    category = console.input(
        "[cyan]Category (e.g. food, transport, rent): [/cyan]").strip().lower()
    date = console.input("[cyan]Date (YYYY-MM-DD): [/cyan]")
    note = console.input("[cyan]Note (optional): [/cyan]")

    new_expense = Expense(amount, category, date, note)
    expenses.append(new_expense)
    save_expenses(expenses)
    console.print("[bold green]Expense added![/bold green]")

    if category in budgets:
        spent = group_by_category(expenses).get(category, 0)
        if spent > budgets[category]:
            console.print(
                f"[bold red]Warning: {category} is now ${spent:.2f}, "
                f"over its ${budgets[category]:.2f} budget![/bold red]")
    console.print()


def view_expenses(expenses):
    console.print(Panel("All Expenses", style="bold cyan"))
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("Date")
    table.add_column("Category")
    table.add_column("Amount", justify="right")
    table.add_column("Note")

    for e in sorted(expenses, key=lambda e: e.date):
        table.add_row(e.id, e.date, e.category, f"${e.amount:.2f}", e.note)

    console.print(table)
    console.print(f"[bold]Total:[/bold] [green]${total_amount(expenses):.2f}[/green]\n")


def monthly_summary(expenses):
    console.print(Panel("Monthly Summary", style="bold cyan"))
    month = console.input("[cyan]Enter month (YYYY-MM): [/cyan]")

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


def edit_expense(expenses):
    console.print(Panel("Edit Expense", style="bold cyan"))
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    view_expenses(expenses)
    expense_id = console.input("[cyan]Enter the ID to edit: [/cyan]").strip()
    target = find_expense(expenses, expense_id)
    if not target:
        console.print("[red]No expense with that ID.[/red]\n")
        return

    console.print("[dim]Press Enter to keep the current value.[/dim]")

    raw_amount = console.input(f"[cyan]Amount [{target.amount}]: $[/cyan]")
    if raw_amount.strip():
        try:
            target.amount = float(raw_amount)
        except ValueError:
            console.print("[red]Invalid amount, keeping the old value.[/red]")

    raw_category = console.input(f"[cyan]Category [{target.category}]: [/cyan]")
    if raw_category.strip():
        target.category = raw_category.strip().lower()

    raw_date = console.input(f"[cyan]Date [{target.date}]: [/cyan]")
    if raw_date.strip():
        target.date = raw_date.strip()

    raw_note = console.input(f"[cyan]Note [{target.note}]: [/cyan]")
    if raw_note.strip():
        target.note = raw_note

    save_expenses(expenses)
    console.print("[bold green]Expense updated![/bold green]\n")


def delete_expense(expenses):
    console.print(Panel("Delete Expense", style="bold cyan"))
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    view_expenses(expenses)
    expense_id = console.input("[cyan]Enter the ID to delete: [/cyan]").strip()
    target = find_expense(expenses, expense_id)
    if not target:
        console.print("[red]No expense with that ID.[/red]\n")
        return

    confirm = console.input(
        f"[red]Delete {target.date} | {target.category} | ${target.amount:.2f}? (y/n): [/red]")
    if confirm.strip().lower() == "y":
        expenses.remove(target)
        save_expenses(expenses)
        console.print("[bold green]Expense deleted.[/bold green]\n")
    else:
        console.print("[yellow]Cancelled.[/yellow]\n")


def manage_budgets(expenses, budgets):
    console.print(Panel("Budgets", style="bold cyan"))
    console.print("[cyan]1.[/cyan] Set a budget")
    console.print("[cyan]2.[/cyan] View budget status")
    choice = console.input("[bold]Choose an option: [/bold]")

    if choice == "1":
        category = console.input("[cyan]Category: [/cyan]").strip().lower()
        limit = read_amount("[cyan]Monthly budget: $[/cyan]")
        budgets[category] = limit
        save_budgets(budgets)
        console.print(f"[bold green]Budget set: {category} -> ${limit:.2f}[/bold green]\n")
        return

    if choice == "2":
        if not budgets:
            console.print("[yellow]No budgets set yet.[/yellow]\n")
            return

        spent = group_by_category(expenses)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category")
        table.add_column("Spent", justify="right")
        table.add_column("Budget", justify="right")
        table.add_column("Status")

        for category, limit in budgets.items():
            amount = spent.get(category, 0)
            status = "[red]Over[/red]" if amount > limit else "[green]OK[/green]"
            table.add_row(category, f"${amount:.2f}", f"${limit:.2f}", status)

        console.print(table)
        console.print()
        return

    console.print("[red]Invalid option.[/red]\n")


def spending_chart(expenses):
    console.print(Panel("Spending by Category", style="bold cyan"))
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    totals = group_by_category(expenses)
    max_amount = max(totals.values())
    bar_width = 40

    for category, amount in sorted(totals.items(), key=lambda item: -item[1]):
        filled = int((amount / max_amount) * bar_width) if max_amount else 0
        bar = "█" * filled
        console.print(f"{category:12} [green]{bar}[/green] ${amount:.2f}")
    console.print()


def export_csv(expenses):
    console.print(Panel("Export to CSV", style="bold cyan"))
    if not expenses:
        console.print("[yellow]No expenses recorded yet.[/yellow]\n")
        return

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "category", "amount", "note"])
        for e in sorted(expenses, key=lambda e: e.date):
            writer.writerow([e.id, e.date, e.category, e.amount, e.note])

    console.print(f"[bold green]Exported to {CSV_FILE}[/bold green]\n")


def main():
    expenses = load_expenses()
    budgets = load_budgets()

    while True:
        console.print(Panel("[bold]Expense Tracker[/bold]", style="bold blue"))
        console.print("[cyan]1.[/cyan] Add expense")
        console.print("[cyan]2.[/cyan] View all expenses")
        console.print("[cyan]3.[/cyan] Monthly summary")
        console.print("[cyan]4.[/cyan] Edit expense")
        console.print("[cyan]5.[/cyan] Delete expense")
        console.print("[cyan]6.[/cyan] Budgets")
        console.print("[cyan]7.[/cyan] Spending chart")
        console.print("[cyan]8.[/cyan] Export to CSV")
        console.print("[cyan]9.[/cyan] Exit")
        choice = console.input("\n[bold]Choose an option: [/bold]")

        if choice == "1":
            add_expense(expenses, budgets)
        elif choice == "2":
            view_expenses(expenses)
        elif choice == "3":
            monthly_summary(expenses)
        elif choice == "4":
            edit_expense(expenses)
        elif choice == "5":
            delete_expense(expenses)
        elif choice == "6":
            manage_budgets(expenses, budgets)
        elif choice == "7":
            spending_chart(expenses)
        elif choice == "8":
            export_csv(expenses)
        elif choice == "9":
            console.print("[bold red]Goodbye.[/bold red]")
            break
        else:
            console.print("[red]Invalid option, try again.[/red]\n")


if __name__ == "__main__":
    main()
