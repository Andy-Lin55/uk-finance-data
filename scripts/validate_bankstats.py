"""Validate the persisted UK banking panel before publishing it."""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import math
from pathlib import Path

FIELDS = (
    "date",
    "consumer_credit_total_gbp_m",
    "consumer_credit_credit_card_gbp_m",
    "consumer_credit_other_gbp_m",
    "mortgage_approvals_house_purchase",
    "m4_amount_outstanding_gbp_m",
)
LATEST_REQUIRED = (
    "consumer_credit_credit_card_gbp_m",
    "mortgage_approvals_house_purchase",
    "m4_amount_outstanding_gbp_m",
)


def read_panel(path: Path) -> dict[dt.date, dict[str, float | None]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(f"{path}: unexpected columns")
        panel = {}
        for row in reader:
            date = dt.date.fromisoformat(row["date"])
            if date in panel:
                raise ValueError(f"{path}: duplicate date {date}")
            if date.day != calendar.monthrange(date.year, date.month)[1]:
                raise ValueError(f"{path}: {date} is not a month-end date")
            values = {}
            for field in FIELDS[1:]:
                value = row[field]
                number = None if value in (None, "") else float(value)
                if number is not None and (not math.isfinite(number) or number < 0):
                    raise ValueError(f"{path}: invalid {field} on {date}")
                values[field] = number
            panel[date] = values
    if len(panel) < 12:
        raise ValueError(f"{path}: fewer than 12 months")
    if list(panel) != sorted(panel):
        raise ValueError(f"{path}: dates are not ascending")
    if max(panel) > dt.date.today():
        raise ValueError(f"{path}: future observation")
    for field in FIELDS[1:]:
        if not any(row[field] is not None for row in panel.values()):
            raise ValueError(f"{path}: no values in {field}")
    for field in LATEST_REQUIRED:
        if panel[max(panel)][field] is None:
            raise ValueError(f"{path}: latest month missing {field}")
    return panel


def validate(current: Path, previous: Path | None = None) -> tuple[int, dt.date]:
    panel = read_panel(current)
    if previous is not None:
        old = read_panel(previous)
        if not set(old).issubset(panel):
            raise ValueError("previous reporting months disappeared")
        for date, old_values in old.items():
            for field, value in old_values.items():
                if value is not None and panel[date][field] is None:
                    raise ValueError(f"previous {field} value disappeared on {date}")
    return len(panel), max(panel)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    count, latest = validate(args.current, args.previous)
    print(f"Validated {count} months through {latest}")
