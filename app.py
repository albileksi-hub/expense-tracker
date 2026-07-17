"""Web front end for the expense tracker, built on Flask.

Reuses the same data layer as the CLI (expense.py, reports.py, storage.py) and
the same input rules (validation.py). Adds multi-account login on top: each
account gets its own isolated expenses and budgets.
"""

import json
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, redirect, render_template, request, send_file, session, url_for,
)

import auth
import insights
import receipt
from expense import Expense
from reports import filter_by_month, group_by_category, over_budget_categories, total_amount
from storage import (
    export_csv,
    load_budgets,
    load_expenses,
    save_budgets,
    save_expenses,
)
from validation import ValidationError, parse_amount, parse_category, parse_date

app = Flask(__name__)
# In production this must come from the environment; the fallback is dev-only.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB cap on uploads


# ---------- auth helpers ----------

def current_user() -> str | None:
    return session.get("user")


def login_required(view):
    """Redirect to the login page if no one is signed in."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def pro_required(view):
    """Send non-Pro accounts to the upgrade page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("login"))
        if not auth.is_pro(current_user()):
            return redirect(url_for("upgrade"))
        return view(*args, **kwargs)
    return wrapped


def current_month() -> str:
    """Today's month as a canonical 'YYYY-MM' string."""
    return datetime.now().strftime("%Y-%m")


def render_dashboard(error: str | None = None):
    """Render the signed-in user's dashboard, optionally with an error banner."""
    user = current_user()
    expenses = load_expenses(user)
    budgets = load_budgets(user)
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


@app.before_request
def drop_stale_session():
    """If the logged-in account no longer exists (e.g. the accounts file was
    reset), clear the session so the user is cleanly logged out instead of
    ending up in a broken half-signed-in state."""
    user = session.get("user")
    if user is not None and not auth.user_exists(user):
        session.pop("user", None)


@app.context_processor
def inject_pro_status():
    """Make the current account's Pro status available to every template."""
    user = current_user()
    return {"is_pro": user is not None and auth.is_pro(user)}


# ---------- auth routes ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user() is not None:
        return redirect(url_for("index"))
    if request.method == "POST":
        try:
            username = auth.register(
                request.form.get("username"), request.form.get("password"))
        except auth.AuthError as err:
            return render_template("register.html", error=str(err))
        session["user"] = username
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user() is not None:
        return redirect(url_for("index"))
    if request.method == "POST":
        try:
            username = auth.authenticate(
                request.form.get("username"), request.form.get("password"))
        except auth.AuthError as err:
            return render_template("login.html", error=str(err))
        session["user"] = username
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


# ---------- public landing ----------

@app.route("/")
def home():
    user = current_user()
    stats = None
    if user is not None:
        expenses = load_expenses(user)
        stats = {
            "total": total_amount(expenses),
            "count": len(expenses),
            "categories": len(group_by_category(expenses)),
        }
    return render_template("home.html", stats=stats)


# ---------- expense routes (all require login) ----------

@app.route("/dashboard")
@login_required
def index():
    return render_dashboard()


@app.route("/add", methods=["POST"])
@login_required
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

    user = current_user()
    expenses = load_expenses(user)
    expenses.append(expense)
    save_expenses(expenses, user)
    return redirect(url_for("index"))


@app.route("/scan", methods=["POST"])
@login_required
def scan():
    """Read an uploaded receipt photo and show a pre-filled review form."""
    upload = request.files.get("receipt")
    if upload is None or not upload.filename:
        return render_dashboard(error="Please choose a receipt image to scan.")

    blank = {"amount": "", "category": "", "date": "", "note": ""}
    try:
        image_b64, media_type = receipt.prepare_image(upload.stream)
        fields = receipt.extract_receipt(image_b64, media_type)
    except receipt.ReceiptError as err:
        # Fall back to a manual review form so the feature still works.
        return render_template("review.html", fields=blank, message=str(err))

    return render_template("review.html", fields=fields, message=None)


@app.errorhandler(413)
def handle_too_large(err):
    return render_dashboard(error="That image is too large — please upload one under 10 MB.")


@app.route("/edit/<expense_id>", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    user = current_user()
    expenses = load_expenses(user)
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
        save_expenses(expenses, user)
        return redirect(url_for("index"))

    return render_template("edit.html", expense=target)


@app.route("/delete/<expense_id>", methods=["POST"])
@login_required
def delete(expense_id):
    user = current_user()
    expenses = [e for e in load_expenses(user) if e.id != expense_id]
    save_expenses(expenses, user)
    return redirect(url_for("index"))


@app.route("/summary")
@login_required
def summary():
    expenses = load_expenses(current_user())
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
@login_required
def budgets():
    user = current_user()
    budget_map = load_budgets(user)
    expenses = load_expenses(user)
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
        save_budgets(budget_map, user)
        return redirect(url_for("budgets"))

    spent = group_by_category(filter_by_month(expenses, month))
    return render_template(
        "budgets.html", current_month=month, budgets=budget_map, spent=spent)


@app.route("/export.csv")
@login_required
def export():
    path = export_csv(load_expenses(current_user()), current_user())
    return send_file(path, as_attachment=True, download_name="expenses.csv")


# ---------- Pro subscription (mock) + AI insights ----------

@app.route("/upgrade", methods=["GET", "POST"])
@login_required
def upgrade():
    user = current_user()
    if request.method == "POST":
        # Mock subscription: no real payment is taken — this just flips the flag.
        auth.set_pro(user, True)
        return redirect(url_for("insights_view"))
    return render_template("upgrade.html", already_pro=auth.is_pro(user))


@app.route("/downgrade", methods=["POST"])
@login_required
def downgrade():
    auth.set_pro(current_user(), False)
    return redirect(url_for("upgrade"))


@app.route("/insights")
@pro_required
def insights_view():
    expenses = load_expenses(current_user())
    local = insights.local_insights(expenses)

    opinion = None
    opinion_error = None
    try:
        opinion = insights.ai_opinion(expenses)
    except insights.InsightsError as err:
        opinion_error = str(err)

    return render_template(
        "insights.html", local=local, opinion=opinion, opinion_error=opinion_error)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
