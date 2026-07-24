"""UK banking / monetary-financial-institutions (MFI) aggregates.

Sector-level banking data comes from BoE IADB money & credit series
(Bankstats tables A-D are published as these time series). This avoids
guessing the changing Bankstats XLSX URL and gives a stable, scriptable feed.

For granular per-table Bankstats detail, drop the downloaded XLSX into
`raw/` and this module will parse it (see `parse_bankstats_xlsx`).

Usage:
    from fetch_bankstats import fetch_banking_aggregates
    df = fetch_banking_aggregates(start="01/Jan/2015")
"""
from __future__ import annotations

import os

from boe_iadb import fetch_series

# Sector banking aggregates (Bankstats / money & credit tables as IADB series).
# Codes verified against the live IADB endpoint (see charlescoverdale/boe R pkg).
BANKING_SERIES = {
    # Consumer credit outstanding (GBP m, SA, monthly, from Apr 1993)
    "LPMVZRI": "consumer_credit_total_gbp_m",
    "LPMVZRJ": "consumer_credit_credit_card_gbp_m",
    "LPMVZRK": "consumer_credit_other_gbp_m",
    # Secured lending / mortgage approvals for house purchase (SA, monthly)
    "LPMVTVX": "mortgage_approvals_house_purchase",
    # M4 broad money amounts outstanding (GBP m, SA, monthly, from 1982)
    "LPMAUYN": "m4_amount_outstanding_gbp_m",
}


def fetch_banking_aggregates(start="01/Jan/2015", end=None):
    df = fetch_series(list(BANKING_SERIES.keys()), start=start, end=end)
    df = df.rename(columns=BANKING_SERIES)
    return df


def parse_bankstats_xlsx(path: str):
    """Parse a downloaded Bankstats XLSX (raw/) into per-table DataFrames."""
    import pandas as pd

    if not os.path.exists(path):
        raise FileNotFoundError(path)
    xl = pd.ExcelFile(path)
    tables = {}
    for sheet in xl.sheet_names:
        try:
            tables[sheet] = xl.parse(sheet, header=None)
        except Exception:
            continue
    return tables


def save_processed(df, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    df = fetch_banking_aggregates(start="01/Jan/2020")
    out = os.path.join(root, "processed", "banking_aggregates.csv")
    save_processed(df, out)
    print("wrote", out, "rows", len(df))
    print(df.tail(3).to_string(index=False))
