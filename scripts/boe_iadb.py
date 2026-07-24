"""Bank of England Interactive Statistical Database (IADB) client.

No API token required. Fetches series as CSV from the public IADB endpoint.

Curated series cover money & credit, consumer credit, and policy/FX rates.
Series codes follow the BoE IADB naming (e.g. IUDBEDR = Bank Rate).

Usage:
    from boe_iadb import fetch_series, CURATED_SERIES
    df = fetch_series(["IUDBEDR"], start="01/Jan/2020", end="31/Dec/2024")
"""
from __future__ import annotations

import io
import urllib.parse
import urllib.request

IADB_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"

# Curated UK series (code -> human label). Mirrors the Mexico macro curated set.
# Codes verified against the live IADB endpoint.
CURATED_SERIES = {
    # Policy & money-market rates
    "IUDBEDR": "Bank Rate (official bank rate)",
    "IUDSOIA": "SONIA (Sterling Overnight Index Average)",
    # FX (foreign currency per GBP)
    "XUDLUSS": "USD/GBP spot (US$ per GBP)",
    "XUDLERS": "EUR/GBP spot (EUR per GBP)",
    "XUDLJYS": "JPY/GBP spot",
    # Consumer credit outstanding (GBP m, SA)
    "LPMVZRI": "Consumer credit total outstanding (GBP m)",
    "LPMVZRJ": "Consumer credit - credit cards (GBP m)",
    "LPMVZRK": "Consumer credit - other (GBP m)",
    # Mortgage / housing
    "LPMVTVX": "Mortgage approvals for house purchase (SA)",
    # Broad money
    "LPMAUYN": "M4 broad money outstanding (GBP m, SA)",
}


def _fetch_csv(series_codes: list[str], start: str, end: str) -> str:
    """Hit the IADB CSV endpoint and return raw CSV text."""
    params = {
        "csv.x": "yes",
        "Datefrom": start,
        "Dateto": end,
        "SeriesCodes": ",".join(series_codes),
        "CSVF": "TN",
        "UsingCodes": "Y",
        "VPD": "Y",
        "VFD": "N",
    }
    url = IADB_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "uk-finance-data/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_series(series_codes=None, start="01/Jan/2015", end=None):
    """Fetch one or more IADB series into a tidy pandas DataFrame.

    Returns DataFrame with a 'date' column and one column per series code.
    """
    import pandas as pd

    if series_codes is None:
        series_codes = list(CURATED_SERIES.keys())
    if end is None:
        import datetime
        end = datetime.date.today().strftime("%d/%b/%Y")

    csv_text = _fetch_csv(series_codes, start, end)
    df = pd.read_csv(io.StringIO(csv_text))
    df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"], format="%d %b %Y", errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    return df


def latest(series_codes=None):
    """Return the most recent observation for each curated series as a dict."""
    df = fetch_series(series_codes)
    out = {}
    for col in df.columns:
        if col == "date":
            continue
        s = df[["date", col]].dropna()
        if len(s):
            out[col] = {
                "label": CURATED_SERIES.get(col, col),
                "date": s["date"].iloc[-1].strftime("%Y-%m-%d"),
                "value": float(s[col].iloc[-1]),
            }
    return out


if __name__ == "__main__":
    import sys
    codes = sys.argv[1:] or ["IUDBEDR", "IUDSOIA", "XUDLUSS"]
    df = fetch_series(codes, start="01/Jan/2023")
    print(df.tail())
