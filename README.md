# Expense Tracker

An expense tracker written in Python, available both as a terminal app (built on
[rich](https://github.com/Textualize/rich)) and as a web app (built on Flask).
Both share the same data file, so you can use either interchangeably.

## Features

- **Multiple accounts** (web app) — sign up, log in, and each account keeps its
  own private expenses and budgets
- Add, view, edit, and delete expenses (each entry gets a short unique ID)
- Monthly summaries with per-category totals
- Category budgets with over-budget warnings
- Spending bar chart
- Export to CSV
- Data persisted as JSON — human-readable and diff-friendly
- Validated input: bad amounts and impossible dates are rejected, not crashed on

## A note on the login system

Passwords are hashed with `werkzeug.security` (scrypt) and never stored in plain
text. This is a **learning-grade** auth layer, though: the accounts file
(`users.json`) and per-account data (`user_data/`) are git-ignored so they're
never committed, and you should use a throwaway password. In production the Flask
`SECRET_KEY` would come from the environment (`SECRET_KEY=... python3 app.py`)
rather than the built-in dev fallback.

## Getting started

```bash
pip install -r requirements.txt

python3 main.py   # terminal version
python3 app.py    # web version, then open http://localhost:5050
```

## Running the tests

```bash
python3 -m pytest -v
```

## Project layout

| File | Role |
| --- | --- |
| `main.py` | Terminal menu, prompts, and display |
| `app.py` | Flask routes for the web version |
| `templates/`, `static/` | HTML templates and CSS for the web version |
| `expense.py` | The `Expense` dataclass and its JSON (de)serialization |
| `reports.py` | Pure calculation functions (filtering, totals, budget checks) |
| `storage.py` | Persistence: per-account JSON save/load and CSV export |
| `validation.py` | Input rules (amount, date, category) shared by both front ends |
| `auth.py` | Account registration and password hashing (web app) |
| `test_*.py` | Unit tests for validation, storage, reports, auth, and the web routes |

The calculation logic (`reports.py`), the data layer (`storage.py`), and the
input rules (`validation.py`) are shared, unmodified, between the terminal and
web versions — only the interface on top differs. Because `validation.py` is the
single source of truth for what counts as valid input, the CLI and the web app
reject exactly the same bad input; the only difference is that the CLI re-prompts
while the web app re-renders the form with an error banner. `reports.py` is free
of input/output entirely, so every business rule can be unit-tested without
simulating a terminal session or an HTTP request.

## A note on money and `float`

Amounts are stored as `float` for simplicity. For a real financial app you'd use
`decimal.Decimal` to avoid binary floating-point rounding (e.g. `0.1 + 0.2`);
`float` is a deliberate trade-off here for a small personal tracker.
