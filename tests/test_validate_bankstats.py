import csv
import tempfile
import unittest
from pathlib import Path

from scripts.validate_bankstats import FIELDS, validate


def write_panel(path, months=12, missing_total=False):
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        for index in range(months):
            year, month = 2025 + index // 12, index % 12 + 1
            date = f"{year}-{month:02d}-" + ("28" if month == 2 else "30" if month in (4, 6, 9, 11) else "31")
            writer.writerow([date, "" if missing_total and index == months - 1 else 100, 20, 80, 1000, 2000])


class ValidationTests(unittest.TestCase):
    def test_accepts_new_month_with_unpublished_credit_total(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path(directory) / "old.csv"
            new = Path(directory) / "new.csv"
            write_panel(old, 12)
            write_panel(new, 13, missing_total=True)
            self.assertEqual(validate(new, old)[0], 13)

    def test_rejects_lost_historical_value(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path(directory) / "old.csv"
            new = Path(directory) / "new.csv"
            write_panel(old)
            write_panel(new)
            content = new.read_text().replace("2025-01-31,100,20", "2025-01-31,,20")
            new.write_text(content)
            with self.assertRaisesRegex(ValueError, "disappeared"):
                validate(new, old)

    def test_rejects_missing_latest_core_metric(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "new.csv"
            write_panel(path)
            path.write_text(path.read_text().replace("2025-12-31,100,20,80,1000", "2025-12-31,100,20,80,"))
            with self.assertRaisesRegex(ValueError, "latest month missing"):
                validate(path)


if __name__ == "__main__":
    unittest.main()
