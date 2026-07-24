# uk-finance-data

A Mexico-style integrated UK financial data pipeline + MCP server. Three tiers,
one entry point — macro, banking sector, and listed companies.

Modelled on the `Mexico/Industry data` repo structure.

## Three tiers

| Tier | Source | Tool / module | Notes |
|---|---|---|---|
| **1. Macro** | Bank of England IADB + ONS | `boe_series`, `ons_data` | No API token. BoE policy/FX/credit rates; ONS CPI/unemployment/GDP. |
| **2. Banking sector** | BoE IADB money & credit series (Bankstats A–D) | `bankstats` | Consumer credit, mortgage approvals, M4 broad money. |
| **3. Listed companies** | Yahoo Finance (`.L` tickers) | `lse_price`, `lse_financials` | LSE issuers; `.L` added if missing. |

## Layout

```
scripts/
  boe_iadb.py         # BoE IADB client (no token), curated UK series
  ons_client.py       # ONS CSV-generator client (old API retired 25/11/2024)
  fetch_bankstats.py  # banking/MFI aggregates -> processed/banking_aggregates.csv
  lse_companies.py    # LSE quick fundamentals via yfinance
  uk_mcp.py           # MCP server (uv inline deps: mcp, pandas, yfinance)
processed/            # tidy CSV outputs
raw/                  # drop Bankstats XLSX here for granular per-table parsing
analysis/             # notebooks / reports
```

## Run the MCP server

```bash
uv run --script scripts/uk_mcp.py
```

Or register it (Claude / WorkBuddy `mcp.json`):

```json
{
  "mcpServers": {
    "uk": {
      "command": "uv",
      "args": ["run", "--script", "<abs path>/scripts/uk_mcp.py"],
      "env": {}
    }
  }
}
```

## Refresh banking aggregates

```bash
python3 scripts/fetch_bankstats.py   # writes processed/banking_aggregates.csv
```

## Data caveats

- **BoE IADB** is token-free and stable; series codes verified against the live
  endpoint (see `charlescoverdale/boe` R package for the canonical mappings).
- **ONS**: the legacy `api.ons.gov.uk` was retired 2024-11-25; this uses the
  public CSV generator. Headline CDIDs only (CPI/CPIH, unemployment, GDP).
- **Bankstats**: granular per-table detail is published as a changing-URL XLSX.
  Drop it into `raw/` and call `parse_bankstats_xlsx()`. Aggregate series here
  are the stable scriptable feed.
- **Coverage gaps**: recent consumer-credit *total* can be NaN while
  subcomponents publish ahead (same pattern as Mexico's CNBV gaps).
- **LSE/yfinance**: Yahoo rate-limits aggressively; the tools return
  `{"error": ...}` instead of raising — retry after a pause.
