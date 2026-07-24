# Data pipeline notes

How each tier is sourced and refreshed, plus known breaks.

## Tier 1 — Macro

### Bank of England IADB
- Endpoint: `https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp`
- CSV via `csv.x=yes&SeriesCodes=...&UsingCodes=Y&CSVF=TN&VPD=Y`, dates `DD/Mon/YYYY`.
- **No token.** Up to 300 codes per request.
- Curated codes (verified live): `IUDBEDR` Bank Rate, `IUDSOIA` SONIA,
  `XUDLUSS/XUDLERS/XUDLJYS` FX, `LPMVZRI/J/K` consumer credit, `LPMVTVX`
  mortgage approvals, `LPMAUYN` M4 outstanding.
- Reference for canonical code mappings: `github.com/charlescoverdale/boe`.

### ONS
- Legacy `api.ons.gov.uk` **retired 2024-11-25** (HTTP 404 + decommission notice).
- Working route: public CSV generator
  `https://www.ons.gov.uk/generator?format=csv&uri=/{topic}/timeseries/{cdid}/{dataset}`
- Needs the **full topic path**, not just the cdid:
  - CPI/CPIH: `economy/inflationandpriceindices/timeseries/{cdid}/mm23`
  - Unemployment: `employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms`
  - GDP: `economy/grossdomesticproductgdp/timeseries/{cdid}/qna`
- Headline CDIDs: `L55O` CPIH, `D7G7` CPI, `MGSX` unemployment, `IHYQ` GDP growth, `ABMI` GDP level.

## Tier 2 — Banking sector
- Aggregate banking data comes from the same BoE IADB money & credit series
  (Bankstats tables A–D are published as these time series). This is the stable,
  scriptable feed — no XLSX URL guessing.
- Refresh: `python3 scripts/fetch_bankstats.py` → `processed/banking_aggregates.csv`.
- Granular per-table Bankstats detail: download the current XLSX from the BoE
  statistics page into `raw/`, then `parse_bankstats_xlsx(path)`.

## Tier 3 — Listed companies
- Yahoo Finance `.L` tickers via `yfinance`. `.L` suffix auto-added.
- Yahoo **rate-limits aggressively**; tools return `{"error": ...}` on throttle.
  Retry after a pause. No local persistence by default.

## Known coverage gaps / breaks
- Recent consumer-credit **total** (`LPMVZRI`) can lag its subcomponents
  (`LPMVZRJ/K`) by a month — recent total rows may be NaN. Real coverage gap,
  not a bug (same pattern as Mexico CNBV).
- ONS headline set is intentionally narrow; extend `HEADLINE_SERIES` with more
  CDIDs as needed.
