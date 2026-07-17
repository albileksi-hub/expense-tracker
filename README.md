# Expense Tracker

An expense tracker written in Python, available both as a terminal app (built on
[rich](https://github.com/Textualize/rich)) and as a web app (built on Flask).
Both share the same data file, so you can use either interchangeably.

## Features

- Add, view, edit, and delete expenses (each entry gets a short unique ID)
- Monthly summaries with per-category totals
- Category budgets with over-budget warnings
- Spending bar chart
- Export to CSV
- Data persisted as JSON — human-readable and diff-friendly
- Validated input: bad amounts and impossible dates are rejected, not crashed on

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
| `storage.py` | Persistence: JSON save/load and CSV export |
| `test_reports.py` | Unit tests for the model and report logic |

The calculation logic in `reports.py` and the data layer in `storage.py` are
shared, unmodified, between the terminal and web versions — only the interface
on top differs. `reports.py` is also free of input/output entirely, so every
business rule can be unit-tested without simulating a terminal session or an
HTTP request.
