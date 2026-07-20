"""Web front end for the expense tracker, built on Flask.

Reuses the same data layer as the CLI (expense.py, reports.py, storage.py) and
the same input rules (validation.py). Adds multi-account login on top: each
account gets its own isolated expenses and budgets.
"""

import json
import os
import secrets
import sqlite3
from calendar import month_abbr
from datetime import datetime
from functools import wraps

from flask import (
    Flask, redirect, render_template, request, send_file, session, url_for,
)

import auth
import insights
import receipt
from expense import Expense
from reports import (
    filter_by_month,
    group_by_category,
    monthly_totals,
    over_budget_categories,
    total_amount,
)
from storage import (
    add_expense,
    delete_expense,
    export_csv,
    get_expense,
    load_budgets,
    load_expenses,
    set_budget,
    update_expense,
)
from validation import ValidationError, parse_amount, parse_category, parse_date

app = Flask(__name__)
# In production this must come from the environment; the fallback is dev-only.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB cap on uploads


# ---------- CSRF protection ----------

def csrf_token() -> str:
    """The session's CSRF token, creating it on first use."""
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(32)
    return session["_csrf"]


@app.context_processor
def inject_csrf():
    return {"csrf_token": csrf_token}


@app.before_request
def check_csrf():
    """Reject any POST whose form token doesn't match the session's token."""
    if request.method != "POST" or not app.config.get("CSRF_ENABLED", True):
        return None
    sent = request.form.get("_csrf", "")
    expected = session.get("_csrf", "")
    if not expected or not secrets.compare_digest(sent, expected):
        return render_template(
            "error.html",
            title="Request blocked",
            message="The form's security token was missing or invalid. "
                    "Go back, refresh the page, and try again."), 400


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
    """Send non-Pro accounts to the upgrade page (and anonymous ones to login)."""
    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not auth.is_pro(current_user()):
            return redirect(url_for("upgrade"))
        return view(*args, **kwargs)
    return wrapped


def current_month() -> str:
    """Today's month as a canonical 'YYYY-MM' string."""
    return datetime.now().strftime("%Y-%m")


@app.template_filter("money")
def money(amount, decimals=2) -> str:
    """Format 1276.04 as $1,276.04 (or $1,276 with decimals=0)."""
    return f"${amount:,.{decimals}f}"


@app.template_filter("hue")
def category_hue(name: str) -> int:
    """A stable 0-359 hue for a category name, for its color dot.

    Not Python's hash(), which is salted per process — colors must not change
    between restarts.
    """
    return sum(ord(c) * 31 for c in name) % 360


def trend_chart(series, width=720, height=220):
    """Turn a [(YYYY-MM, total), ...] series into SVG-ready geometry."""
    pad_l, pad_r, pad_t, pad_b = 46, 16, 26, 34
    max_amount = max((amount for _, amount in series), default=0.0) or 1.0
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    baseline = pad_t + plot_h
    count = len(series)

    dots = []
    for i, (month_key, amount) in enumerate(series):
        x = pad_l + (plot_w * i / (count - 1) if count > 1 else plot_w / 2)
        y = pad_t + plot_h * (1 - amount / max_amount)
        dots.append({
            "x": round(x, 1), "y": round(y, 1), "amount": amount,
            "label": month_abbr[int(month_key[5:7])],
        })

    line_points = " ".join(f"{d['x']},{d['y']}" for d in dots)
    area = ""
    if dots:
        area = (f"M {dots[0]['x']},{baseline} "
                + " ".join(f"L {d['x']},{d['y']}" for d in dots)
                + f" L {dots[-1]['x']},{baseline} Z")

    return {
        "width": width, "height": height, "baseline": baseline,
        "dots": dots, "line_points": line_points, "area": area,
        "max_amount": max_amount, "has_spending": any(a > 0 for _, a in series),
    }


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
@app.errorhandler(sqlite3.Error)
def handle_corrupt_data(err):
    """Show a friendly page instead of a 500 when the database (or a legacy
    JSON file being migrated) can't be read."""
    return render_template(
        "error.html",
        title="Couldn't load your data",
        message=f"The data store couldn't be read ({err}). "
                "If this keeps happening, check expenses.db and any leftover "
                "JSON data files, then reload."), 500


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

def auth_page(action, template):
    """Shared GET/POST flow for the login and register pages.

    `action` is auth.authenticate or auth.register — the only difference
    between the two pages besides their template.
    """
    if current_user() is not None:
        return redirect(url_for("index"))
    if request.method == "POST":
        try:
            session["user"] = action(
                request.form.get("username"), request.form.get("password"))
            return redirect(url_for("index"))
        except auth.AuthError as err:
            return render_template(template, error=str(err))
    return render_template(template)


@app.route("/register", methods=["GET", "POST"])
def register():
    return auth_page(auth.register, "register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    return auth_page(auth.authenticate, "login.html")


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


def parse_expense_form() -> dict:
    """Validate the four expense fields of the submitted form (or raise)."""
    return {
        "amount": parse_amount(request.form.get("amount")),
        "category": parse_category(request.form.get("category")),
        "date": parse_date(request.form.get("date")),
        "note": request.form.get("note", "").strip(),
    }


@app.route("/add", methods=["POST"])
@login_required
def add():
    try:
        expense = Expense(**parse_expense_form())
    except ValidationError as err:
        return render_dashboard(error=str(err))

    add_expense(expense, current_user())
    return redirect(url_for("index"))


@app.route("/scan", methods=["POST"])
@login_required
def scan():
    """Read an uploaded receipt photo and show a pre-filled review form."""
    upload = request.files.get("receipt")
    if upload is None or not upload.filename:
        return render_dashboard(error="Please choose a receipt image to scan.")

    try:
        fields = receipt.extract_receipt(*receipt.prepare_image(upload.stream))
        message = None
    except receipt.ReceiptError as err:
        # Fall back to a manual review form so the feature still works.
        fields = {"amount": "", "category": "", "date": "", "note": ""}
        message = str(err)
    return render_template("review.html", fields=fields, message=message)


@app.errorhandler(413)
def handle_too_large(err):
    return render_dashboard(error="That image is too large — please upload one under 10 MB.")


@app.route("/edit/<expense_id>", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    user = current_user()
    target = get_expense(expense_id, user)
    if target is None:
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            fields = parse_expense_form()
        except ValidationError as err:
            return render_template("edit.html", expense=target, error=str(err))

        for attr, value in fields.items():
            setattr(target, attr, value)
        update_expense(target, user)
        return redirect(url_for("index"))

    return render_template("edit.html", expense=target)


@app.route("/delete/<expense_id>", methods=["POST"])
@login_required
def delete(expense_id):
    delete_expense(expense_id, current_user())
    return redirect(url_for("index"))


@app.route("/summary")
@login_required
def summary():
    expenses = load_expenses(current_user())
    month = request.args.get("month") or current_month()
    matching = filter_by_month(expenses, month)
    totals = group_by_category(matching)
    trend = trend_chart(monthly_totals(expenses, months=6))

    return render_template(
        "summary.html",
        month=month,
        total=total_amount(matching),
        totals=totals,
        max_amount=max(totals.values()) if totals else 0,
        trend=trend,
    )


@app.route("/budgets", methods=["GET", "POST"])
@login_required
def budgets():
    user = current_user()
    budget_map = load_budgets(user)
    month = current_month()
    spent = group_by_category(filter_by_month(load_expenses(user), month))

    if request.method == "POST":
        try:
            category = parse_category(request.form.get("category"))
            limit = parse_amount(request.form.get("limit"))
        except ValidationError as err:
            return render_template(
                "budgets.html", current_month=month,
                budgets=budget_map, spent=spent, error=str(err))

        set_budget(category, limit, user)
        return redirect(url_for("budgets"))

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
    # The Werkzeug debugger is a code-execution risk if ever exposed, so debug
    # mode is opt-in: FLASK_DEBUG=1 python app.py
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5050)
