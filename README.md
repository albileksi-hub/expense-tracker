# Expense Tracker

A terminal expense tracker written in Python, with a colorful interface built on
[rich](https://github.com/Textualize/rich).

## Features

- Add, view, edit, and delete expenses (each entry gets a short unique ID)
- Monthly summaries with per-category totals
- Category budgets with over-budget warnings
- Spending bar chart, right in the terminal
- Export to CSV
- Data persisted as JSON — human-readable and diff-friendly
- Validated input: bad amounts and impossible dates are rejected, not crashed on

## Getting started

```bash
pip install -r requirements.txt
python3 main.py
```

## Running the tests

```bash
python3 -m pytest -v
```

## Project layout

| File | Role |
| --- | --- |
| `main.py` | Menu, prompts, and display — all the terminal I/O |
| `expense.py` | The `Expense` dataclass and its JSON (de)serialization |
| `reports.py` | Pure calculation functions (filtering, totals, budget checks) |
| `storage.py` | Persistence: JSON save/load and CSV export |
| `test_reports.py` | Unit tests for the model and report logic |

The calculation logic in `reports.py` is deliberately free of input/output, so
every business rule can be unit-tested without simulating a terminal session.
