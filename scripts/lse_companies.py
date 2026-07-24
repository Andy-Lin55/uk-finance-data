"""UK listed companies (LSE) quick fundamentals via Yahoo Finance (.L tickers).

Mirrors the Mexico Tier-3 route: quick price + financials for listed issuers.
Requires yfinance (declared in the MCP script header).

Usage:
    from lse_companies import price, financials
    price("BARC.L")
"""
from __future__ import annotations


def price(ticker: str):
    import yfinance as yf

    t = yf.Ticker(ticker if ticker.endswith(".L") else ticker + ".L")
    try:
        hist = t.history(period="5d")
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "ticker": t.ticker}
    if hist.empty:
        return {"error": f"no price data for {ticker}"}
    last = hist.iloc[-1]
    try:
        currency = t.fast_info.get("currency", "GBp")
    except Exception:
        currency = "GBp"
    return {
        "ticker": t.ticker,
        "date": hist.index[-1].strftime("%Y-%m-%d"),
        "close": float(last["Close"]),
        "currency": currency,
    }


def financials(ticker: str):
    import yfinance as yf

    t = yf.Ticker(ticker if ticker.endswith(".L") else ticker + ".L")
    try:
        inc = t.income_stmt
        bs = t.balance_sheet
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "ticker": t.ticker}
    out = {"ticker": t.ticker}
    for name, frame in (("income_statement", inc), ("balance_sheet", bs)):
        if frame is not None and not frame.empty:
            out[name] = frame.head(15).fillna(0).astype(float).to_dict()
    return out


if __name__ == "__main__":
    print(price("BARC.L"))
