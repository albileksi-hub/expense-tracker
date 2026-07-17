"""Web front end for the expense tracker, built on Flask.

Reuses the same data layer as the CLI (expense.py, reports.py, storage.py) —
this app only adds routes and templates on top.
"""

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

app = Flask(__name__)


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
    expenses = load_expenses()
    budgets = load_budgets()
    current_month = datetime.now().strftime("%Y-%m")
    month_expenses = filter_by_month(expenses, current_month)

    return render_template(
        "index.html",
        expenses=sorted(expenses, key=lambda e: e.date, reverse=True),
        total=total_amount(expenses),
        current_month=current_month,
        over_budget=over_budget_categories(month_expenses, budgets),
    )


@app.route("/add", methods=["POST"])
def add():
    expenses = load_expenses()
    expenses.append(Expense(
        amount=float(request.form["amount"]),
        category=request.form["category"].strip().lower(),
        date=request.form["date"],
        note=request.form.get("note", "").strip(),
    ))
    save_expenses(expenses)
    return redirect(url_for("index"))


@app.route("/edit/<expense_id>", methods=["GET", "POST"])
def edit(expense_id):
    expenses = load_expenses()
    target = next((e for e in expenses if e.id == expense_id), None)
    if target is None:
        return redirect(url_for("index"))

    if request.method == "POST":
        target.amount = float(request.form["amount"])
        target.category = request.form["category"].strip().lower()
        target.date = request.form["date"]
        target.note = request.form.get("note", "").strip()
        save_expenses(expenses)
        return redirect(url_for("index"))

    return render_template("edit.html", expense=target)


@app.route("/delete/<expense_id>", methods=["POST"])
def delete(expense_id):
    expenses = load_expenses()
    expenses = [e for e in expenses if e.id != expense_id]
    save_expenses(expenses)
    return redirect(url_for("index"))


@app.route("/summary")
def summary():
    expenses = load_expenses()
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
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

    if request.method == "POST":
        category = request.form["category"].strip().lower()
        budget_map[category] = float(request.form["limit"])
        save_budgets(budget_map)
        return redirect(url_for("budgets"))

    expenses = load_expenses()
    current_month = datetime.now().strftime("%Y-%m")
    spent = group_by_category(filter_by_month(expenses, current_month))

    return render_template(
        "budgets.html",
        current_month=current_month,
        budgets=budget_map,
        spent=spent,
    )


@app.route("/export.csv")
def export():
    path = export_csv(load_expenses())
    return send_file(path, as_attachment=True, download_name=CSV_FILE.name)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
