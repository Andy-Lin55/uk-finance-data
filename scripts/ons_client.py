"""ONS (Office for National Statistics) data client.

The old api.ons.gov.uk was retired 25/11/2024. This uses the public CSV
generator endpoint, keyed on a CDID series code + full topic path:

    https://www.ons.gov.uk/generator?format=csv&uri=/{topic}/timeseries/{cdid}/{dataset}

Usage:
    from ons_client import fetch_timeseries, HEADLINE_SERIES
    df = fetch_timeseries("L55O")   # CPIH annual inflation rate
"""
from __future__ import annotations

import io
import urllib.request

GENERATOR = "https://www.ons.gov.uk/generator"

# cdid -> (topic path, dataset, label)
HEADLINE_SERIES = {
    "L55O": ("economy/inflationandpriceindices", "mm23", "CPIH annual inflation rate (%)"),
    "D7G7": ("economy/inflationandpriceindices", "mm23", "CPI annual inflation rate (%)"),
    "MGSX": ("employmentandlabourmarket/peoplenotinwork/unemployment", "lms",
             "Unemployment rate 16+ (%, seasonally adjusted)"),
    "LF24": ("employmentandlabourmarket/peopleinwork/employmentandemployeetypes", "lms",
             "Employment rate 16-64 (%, seasonally adjusted)"),
    "IHYQ": ("economy/grossdomesticproductgdp", "qna", "GDP quarterly growth (%, CVM SA)"),
    "ABMI": ("economy/grossdomesticproductgdp", "qna", "GDP at market prices (GBP m, CVM SA)"),
}


def _parse_period(period: str):
    """Parse ONS period labels: '2026 JUN', '2026 Q1', '2026', '2026-07'."""
    import pandas as pd
    p = period.strip()
    for fmt in ("%Y %b", "%Y Q%q", "%Y"):
        try:
            if "Q" in p:
                year, q = p.split()
                month = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}[q.upper()]
                return pd.Timestamp(int(year), month, 1)
            return pd.to_datetime(p, format=fmt, errors="raise")
        except Exception:
            continue
    return pd.to_datetime(p, errors="coerce")


def fetch_timeseries(cdid: str):
    """Fetch an ONS CDID series into a tidy DataFrame (date, <cdid>)."""
    import pandas as pd

    if cdid not in HEADLINE_SERIES:
        raise KeyError(f"unknown cdid {cdid}; known: {list(HEADLINE_SERIES)}")
    topic, dataset, label = HEADLINE_SERIES[cdid]
    uri = f"/{topic}/timeseries/{cdid.lower()}/{dataset}"
    url = f"{GENERATOR}?format=csv&uri={uri}"
    req = urllib.request.Request(url, headers={"User-Agent": "uk-finance-data/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8-sig", errors="replace")

    rows = []
    reader = io.StringIO(text)
    for line in reader:
        line = line.strip().strip('"')
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) != 2:
            continue
        period, value = parts
        # data rows: period starts with a year digit, value parses as float
        if not period or not period[0].isdigit():
            continue
        try:
            v = float(value)
        except (ValueError, TypeError):
            continue
        rows.append((period, v))

    df = pd.DataFrame(rows, columns=["period", cdid])
    if df.empty:
        return df
    df["date"] = df["period"].map(_parse_period)
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df[["date", cdid]]


def latest(cdid: str):
    df = fetch_timeseries(cdid)
    if df.empty:
        return {"error": f"no data for {cdid}"}
    last = df.iloc[-1]
    return {
        "label": HEADLINE_SERIES[cdid][2],
        "date": last["date"].strftime("%Y-%m-%d"),
        "value": float(last[cdid]),
    }


if __name__ == "__main__":
    for cdid in ["L55O", "MGSX", "IHYQ"]:
        df = fetch_timeseries(cdid)
        print(HEADLINE_SERIES[cdid][2], "rows", len(df))
        print(df.tail(2).to_string(index=False), "\n")
