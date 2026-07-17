"""Web front end for the expense tracker, built on Flask.

Reuses the same data layer as the CLI (expense.py, reports.py, storage.py) and
the same input rules (validation.py) — this app only adds routes and templates
on top.
"""

import json
from datetime import datetime

from flask import Flask, redirect, render_template, request, send_file, url_for

from expense import Expense
from reports import filter_by_month, group_by_category, over_budget_categories, total_amount
from storage import (
    CSV_FILE,
    export_csv,
    load_budgets,
    load_expenses,
    save_budgets,
    save_expenses,
)
from validation import ValidationError, parse_amount, parse_category, parse_date

app = Flask(__name__)


def current_month() -> str:
    """Today's month as a canonical 'YYYY-MM' string."""
    return datetime.now().strftime("%Y-%m")


def render_dashboard(error: str | None = None):
    """Render the expenses dashboard, optionally with an error banner."""
    expenses = load_expenses()
    budgets = load_budgets()
    month = current_month()
    return render_template(
        "index.html",
        expenses=sorted(expenses, key=lambda e: e.date, reverse=True),
        total=total_amount(expenses),
        current_month=month,
        over_budget=over_budget_categories(filter_by_month(expenses, month), budgets),
        error=error,
    )


@app.errorhandler(json.JSONDecodeError)
def handle_corrupt_data(err):
    """Show a friendly page instead of a 500 when a data file is invalid JSON."""
    return render_template("error.html", message=str(err)), 500


@app.route("/")
def home():
    expenses = load_expenses()
    return render_template(
        "home.html",
        total=total_amount(expenses),
        count=len(expenses),
        categories=len(group_by_category(expenses)),
    )


@app.route("/dashboard")
def index():
    return render_dashboard()


@app.route("/add", methods=["POST"])
def add():
    try:
        expense = Expense(
            amount=parse_amount(request.form.get("amount")),
            category=parse_category(request.form.get("category")),
            date=parse_date(request.form.get("date")),
            note=request.form.get("note", "").strip(),
        )
    except ValidationError as err:
        return render_dashboard(error=str(err))

    expenses = load_expenses()
    expenses.append(expense)
    save_expenses(expenses)
    return redirect(url_for("index"))


@app.route("/edit/<expense_id>", methods=["GET", "POST"])
def edit(expense_id):
    expenses = load_expenses()
    target = next((e for e in expenses if e.id == expense_id), None)
    if target is None:
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            amount = parse_amount(request.form.get("amount"))
            category = parse_category(request.form.get("category"))
            date = parse_date(request.form.get("date"))
        except ValidationError as err:
            return render_template("edit.html", expense=target, error=str(err))

        target.amount = amount
        target.category = category
        target.date = date
        target.note = request.form.get("note", "").strip()
        save_expenses(expenses)
        return redirect(url_for("index"))

    return render_template("edit.html", expense=target)


@app.route("/delete/<expense_id>", methods=["POST"])
def delete(expense_id):
    expenses = [e for e in load_expenses() if e.id != expense_id]
    save_expenses(expenses)
    return redirect(url_for("index"))


@app.route("/summary")
def summary():
    expenses = load_expenses()
    month = request.args.get("month") or current_month()
    matching = filter_by_month(expenses, month)
    totals = group_by_category(matching)

    return render_template(
        "summary.html",
        month=month,
        total=total_amount(matching),
        totals=totals,
        max_amount=max(totals.values()) if totals else 0,
    )


@app.route("/budgets", methods=["GET", "POST"])
def budgets():
    budget_map = load_budgets()
    expenses = load_expenses()
    month = current_month()

    if request.method == "POST":
        try:
            category = parse_category(request.form.get("category"))
            limit = parse_amount(request.form.get("limit"))
        except ValidationError as err:
            spent = group_by_category(filter_by_month(expenses, month))
            return render_template(
                "budgets.html", current_month=month,
                budgets=budget_map, spent=spent, error=str(err))

        budget_map[category] = limit
        save_budgets(budget_map)
        return redirect(url_for("budgets"))

    spent = group_by_category(filter_by_month(expenses, month))
    return render_template(
        "budgets.html", current_month=month, budgets=budget_map, spent=spent)


@app.route("/export.csv")
def export():
    path = export_csv(load_expenses())
    return send_file(path, as_attachment=True, download_name=CSV_FILE.name)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
