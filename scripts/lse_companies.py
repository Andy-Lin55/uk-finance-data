"""UK listed companies (LSE) quick fundamentals via Yahoo Finance (.L tickers).

Mirrors the Mexico Tier-3 route: quick price + financials for listed issuers.
Requires yfinance (declared in the MCP script header).

Yahoo is unofficial and throttles aggressively, so every public function here
returns a plain dict and never raises: on failure you get
``{"error": ..., "retryable": bool}`` so the caller knows whether waiting and
trying again is worth it.

Usage:
    from lse_companies import price, financials
    price("BARC.L")
"""
from __future__ import annotations

import time

# Yahoo quotes LSE equities in pence (GBp), not pounds. Callers that mix these
# up are wrong by 100x, so price() reports both.
_PENCE_PER_POUND = 100.0

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (1.0, 2.0)


def _normalise(ticker: str) -> str:
    """Normalise a user-supplied symbol to a Yahoo LSE ticker.

    Yahoo symbols are upper-case and LSE lines carry a ``.L`` suffix. The
    suffix test must be case-insensitive: a lower-case ``barc.l`` would
    otherwise be treated as un-suffixed and become ``barc.l.L``, which
    resolves to nothing.
    """
    t = (ticker or "").strip().upper()
    if not t:
        return ""
    return t if t.endswith(".L") else t + ".L"


def _diagnose(exc: Exception) -> tuple[str, bool]:
    """Map a raw yfinance/network exception to (message, retryable)."""
    return _diagnose_text(f"{type(exc).__name__}: {exc}")


def _diagnose_text(text: str) -> tuple[str, bool]:
    """Map an error string to (message, retryable)."""
    low = text.lower()

    # Sandboxed/proxied environments reject the host outright; retrying that
    # is pointless until the egress policy changes.
    if "allowlist" in low or "egress" in low:
        return (
            f"network policy blocked Yahoo Finance ({text}). "
            "Allow query1.finance.yahoo.com / query2.finance.yahoo.com.",
            False,
        )
    if "429" in low or "too many requests" in low or "rate limit" in low:
        return (f"Yahoo Finance rate-limited the request ({text}).", True)
    # Yahoo serves an HTML error/block page instead of JSON when throttling,
    # which surfaces as a decode error rather than a clean HTTP status.
    if "jsondecode" in low or "expecting value" in low:
        return (
            f"Yahoo Finance returned a non-JSON response ({text}); "
            "usually throttling or a blocked request.",
            True,
        )
    if "timed out" in low or "timeout" in low:
        return (f"Yahoo Finance request timed out ({text}).", True)
    return (text, False)


_PROBE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/BARC.L"


def _probe_yahoo() -> tuple[bool, str, bool]:
    """Check whether Yahoo is reachable at all: (reachable, message, retryable).

    yfinance swallows transport errors and hands back an empty frame, so an
    empty result alone cannot distinguish "unknown ticker" from "we never
    reached Yahoo". This runs only on the failure path, so it costs nothing
    when data comes back normally.
    """
    import urllib.error
    import urllib.request

    req = urllib.request.Request(_PROBE_URL, headers={"User-Agent": "uk-finance-data/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read(64)
        return True, "", True
    except urllib.error.HTTPError as e:
        try:
            body = e.read(200).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        message, retryable = _diagnose_text(f"HTTP Error {e.code}: {body}")
        return False, message, retryable
    except Exception as e:  # noqa: BLE001 - report, never raise
        message, retryable = _diagnose(e)
        return False, message, retryable


def _attempt(fn):
    """Run ``fn`` with bounded retries on transient (retryable) failures.

    Returns (result, error_dict). Exactly one is None.
    """
    last: tuple[str, bool] = ("unknown error", False)
    for i in range(_MAX_ATTEMPTS):
        try:
            return fn(), None
        except Exception as e:  # noqa: BLE001 - deliberately broad; we report, never raise
            message, retryable = _diagnose(e)
            last = (message, retryable)
            if not retryable or i == _MAX_ATTEMPTS - 1:
                break
            time.sleep(_BACKOFF_SECONDS[min(i, len(_BACKOFF_SECONDS) - 1)])
    return None, {"error": last[0], "retryable": last[1]}


def price(ticker: str):
    """LSE-listed company latest price (Yahoo Finance; .L added if missing).

    Returns close in Yahoo's native unit plus ``close_gbp`` when that unit is
    pence, so the caller cannot silently be off by 100x.
    """
    import yfinance as yf

    symbol = _normalise(ticker)
    if not symbol:
        return {"error": "empty ticker", "retryable": False}

    t = yf.Ticker(symbol)

    hist, err = _attempt(lambda: t.history(period="5d"))
    if err:
        return {**err, "ticker": symbol}

    # yfinance returns an empty frame (rather than raising) both for unknown
    # symbols and for some throttled responses, so retry before giving up.
    for i in range(_MAX_ATTEMPTS - 1):
        if hist is not None and not hist.empty:
            break
        time.sleep(_BACKOFF_SECONDS[min(i, len(_BACKOFF_SECONDS) - 1)])
        hist, err = _attempt(lambda: t.history(period="5d"))
        if err:
            return {**err, "ticker": symbol}

    if hist is None or hist.empty:
        reachable, message, retryable = _probe_yahoo()
        if not reachable:
            return {"error": message, "retryable": retryable, "ticker": symbol}
        return {
            "error": (
                f"no price data for {symbol}; check it is a valid LSE symbol "
                "(Yahoo may also be throttling)"
            ),
            "retryable": True,
            "ticker": symbol,
        }

    last = hist.iloc[-1]
    try:
        currency = t.fast_info.get("currency") or "GBp"
    except Exception:
        currency = "GBp"

    close = float(last["Close"])
    out = {
        "ticker": symbol,
        "date": hist.index[-1].strftime("%Y-%m-%d"),
        "close": close,
        "currency": currency,
    }
    if currency == "GBp":
        out["close_gbp"] = round(close / _PENCE_PER_POUND, 4)
    return out


def _frame_to_dict(frame):
    """Serialise a statement frame with ISO date strings as column keys."""
    trimmed = frame.head(15).fillna(0)
    out = {}
    for col in trimmed.columns:
        key = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
        out[key] = {
            str(row): float(trimmed.at[row, col])
            for row in trimmed.index
            if isinstance(trimmed.at[row, col], (int, float))
        }
    return out


def financials(ticker: str):
    """LSE-listed company income statement & balance sheet (Yahoo Finance)."""
    import yfinance as yf

    symbol = _normalise(ticker)
    if not symbol:
        return {"error": "empty ticker", "retryable": False}

    t = yf.Ticker(symbol)

    frames, err = _attempt(lambda: (t.income_stmt, t.balance_sheet))
    if err:
        return {**err, "ticker": symbol}

    inc, bs = frames
    out = {"ticker": symbol}
    for name, frame in (("income_statement", inc), ("balance_sheet", bs)):
        if frame is not None and not frame.empty:
            out[name] = _frame_to_dict(frame)
    if len(out) == 1:
        reachable, message, retryable = _probe_yahoo()
        if not reachable:
            return {"error": message, "retryable": retryable, "ticker": symbol}
        return {
            "error": f"no financial statements for {symbol}",
            "retryable": True,
            "ticker": symbol,
        }
    return out


if __name__ == "__main__":
    print(price("BARC.L"))
