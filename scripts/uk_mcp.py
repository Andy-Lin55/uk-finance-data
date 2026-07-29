# /// script
# requires-python = ">=3.9"
# dependencies = ["mcp>=1.8.0,<2.0.0", "pandas", "yfinance"]
# ///
"""UK finance data MCP server.

Tools (Tier 1 macro):
  boe_series(series_ids?, start?, end?)  -> BoE IADB curated series (no token)
  ons_data(series_id?, dataset?)         -> ONS headline series (no token)

Tools (Tier 2 banking):
  bankstats(start?)                      -> MFI/consumer-credit aggregates

Tools (Tier 3 listed companies):
  lse_price(ticker)                      -> Yahoo Finance .L price
  lse_financials(ticker)                 -> Yahoo Finance .L income/balance sheet

Run:  uv run --script uk_mcp.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("uk-finance-data")


@mcp.tool()
def boe_series(series_ids: list[str] | None = None, start: str = "01/Jan/2015", end: str | None = None):
    """Bank of England IADB macro series. Omit series_ids for the curated set
    (Bank Rate, SONIA, FX, consumer credit, M4). Dates as DD/Mon/YYYY."""
    from boe_iadb import fetch_series, CURATED_SERIES
    try:
        df = fetch_series(series_ids, start=start, end=end)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "curated": CURATED_SERIES}
    return {
        "curated": CURATED_SERIES,
        "rows": len(df),
        "data": df.tail(200).assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records"),
    }


@mcp.tool()
def ons_data(series_id: str = "L55O"):
    """ONS headline series by CDID. Default L55O = CPIH annual inflation rate.
    Other ids: D7G7 (CPI), MGSX (unemployment), IHYQ (GDP growth), ABMI (GDP level)."""
    from ons_client import fetch_timeseries, HEADLINE_SERIES
    try:
        df = fetch_timeseries(series_id.upper())
    except KeyError as e:
        return {"error": str(e), "headline": HEADLINE_SERIES}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "headline": HEADLINE_SERIES}
    if df.empty:
        return {"error": f"no data for {series_id}"}
    return {
        "headline": {k: v[2] for k, v in HEADLINE_SERIES.items()},
        "rows": len(df),
        "data": df.tail(120).assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records"),
    }


@mcp.tool()
def bankstats(start: str = "01/Jan/2015"):
    """UK banking / MFI aggregates: consumer credit net lending & growth,
    secured lending, mortgage approvals, M4, loans to businesses/SMEs."""
    from fetch_bankstats import fetch_banking_aggregates, BANKING_SERIES
    try:
        df = fetch_banking_aggregates(start=start)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "series": BANKING_SERIES}
    return {
        "series": BANKING_SERIES,
        "rows": len(df),
        "data": df.tail(120).assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records"),
    }


@mcp.tool()
def lse_price(ticker: str):
    """LSE-listed company latest price (Yahoo Finance; .L added if missing)."""
    from lse_companies import price
    return price(ticker)


@mcp.tool()
def lse_financials(ticker: str):
    """LSE-listed company income statement & balance sheet (Yahoo Finance)."""
    from lse_companies import financials
    return financials(ticker)


if __name__ == "__main__":
    mcp.run()
