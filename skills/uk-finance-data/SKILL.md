---
name: uk-finance-data
description: Use when the user asks for UK financial or economic data — macro (Bank of England IADB + ONS — Bank Rate, SONIA, FX, CPI/CPIH, unemployment, GDP), banking-sector data (consumer credit, mortgage approvals, M4 broad money), or listed-company data (LSE issuers — price, income statement, balance sheet). Routes to the `uk` MCP server or this repo's processed datasets.
---

# UK finance data — routing guide

Three tiers. Pick the tool that matches the question; don't scrape when a tool exists.

## Tier 1 — MACRO (BoE + ONS)

Use the **`uk` MCP server** tools (live, token-free):

- `boe_series(series_ids?, start?, end?)` — Bank Rate, SONIA, USD/EUR/JPY per GBP,
  consumer credit outstanding, mortgage approvals, M4. Omit `series_ids` for the curated
  set; dates as `DD/Mon/YYYY`.
- `ons_data(series_id?)` — headline ONS by CDID: `L55O` CPIH, `D7G7` CPI, `MGSX`
  unemployment, `IHYQ` GDP growth, `ABMI` GDP level. Default `L55O`.

Notes:
- BoE IADB covers rates/FX/credit/money; ONS's unique value is **prices + labour + GDP**.
- The legacy `api.ons.gov.uk` was retired 2024-11-25 — this uses the public CSV generator
  with full topic paths. Only the headline CDIDs above are wired in.

## Tier 2 — BANKING SECTOR (BoE money & credit / Bankstats)

- `bankstats(start?)` — consumer credit (total / credit-card / other, GBP m, SA),
  mortgage approvals for house purchase, M4 broad money outstanding. Monthly, stable feed.

For the full panel, read `processed/banking_aggregates.csv` (refresh:
`python3 scripts/fetch_bankstats.py`). Granular per-table Bankstats detail: drop the
current BoE XLSX into `raw/` and call `parse_bankstats_xlsx()`.

**Coverage gap**: recent consumer-credit *total* can be NaN while subcomponents publish
a month ahead — a real gap, not a bug (same as Mexico CNBV).

## Tier 3 — LISTED COMPANIES (LSE issuers)

- `lse_price(ticker)` — latest price (Yahoo Finance; `.L` added if missing).
- `lse_financials(ticker)` — income statement + balance sheet (top rows).

Yahoo **rate-limits aggressively**; tools return `{"error": ...}` on throttle — retry
after a pause rather than hammering.
