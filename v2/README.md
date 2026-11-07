# v2 — Unified Agent Data Store

All agent-level data for the next-generation career dashboard. One source of truth, client-side period derivation, no more parallel Q1/YTD/2025-year data pipelines.

**Status:** schema live as of 2026-04-20. The existing dashboards still read from v1 paths (`/phoenix/`, `/tucson/`, `/market/`, `/listings_*/`, `/brokerage/`, `/hubs/`). The unified career UI will migrate to v2 in a future deploy; old tokenized URLs will redirect here.

## Layout

```
v2/
├── agents/{market}/{prefix}.json        ← metadata + aggregates + 20-tx preview
├── transactions/{market}/{prefix}.json  ← full tx arrays keyed by token (lazy-fetched)
└── meta/generated.json                  ← schema version + build timestamp
```

- `{market}` = `phoenix` or `tucson`
- `{prefix}` = first 2 chars of career token (256 shards per market)
- Token: `md5("{name}|{market}|career".lower())[:8]` — universal agent ID

## Why two files per shard

The dashboard's fast path (stats, period selector, overview) only needs the meta shard (~2 MB PHX, ~0.4 MB TUC). The full transaction list — needed only when the user expands a year or downloads a detailed badge — lives in the transactions shard (~5 MB PHX, ~1 MB TUC) and is fetched lazily.

Result: first paint under 500ms, zero cost for users who don't drill in.

## Agent record schema

```jsonc
{
  "schemaVersion": 2,
  "token": "00a691c6",
  "name": "Justin Schlegel",
  "firstName": "Justin",
  "lastName": "Schlegel",
  "market": "phoenix",
  "office": "RHP Real Estate",          // most-recent = offices[0]
  "offices": ["RHP Real Estate", ...],  // ordered most-recent first
  "tier": "Top 1%",
  "email": "...",
  "phone": "...",
  "license": {
    "status": "Active", "number": "...", "type": "Broker",
    "origDate": "...", "expireDate": "...", "employer": "..."
  },
  "firstClose": "2003-01-15",
  "lastClose": "2026-04-18",
  "yearsActive": 24,
  "rank": {
    "volume":       { "rank": 230, "percentile": 99.8 },
    "transactions": { "rank": 277, "percentile": 99.7 }
  },
  "totals": {
    "closed": {
      "transactions": 1094, "volume": 252451253,
      "listingDeals":  711, "listingVolume":  106523586,
      "buyerDeals":    383, "buyerVolume":    145927667,
      "avgDom": 44.6
    },
    "listingsTaken": {
      "total": 972, "closed": 726, "cancelled": 214, "expired": 26,
      "activePending": 6, "other": 0,
      "closedPct": 74.7, "unsoldPct": 24.7
    }
  },
  "byYear": {
    "2025": { "closed": {...}, "listingsTaken": {...} },
    "2024": { ... }
  },
  "recentTransactions": [    // 20 most-recent, embedded in meta for instant drilldown
    { "mls": "...", "list_date": "...", "close_date": "...",
      "status": "Closed|Cancelled|Expired|Active|Pending|Other",
      "side":   "Listing|Buyer",
      "addr": "...", "city": "...", "zip": "...",
      "listPrice": 275000, "soldPrice": 267000, "dom": 3,
      "office": "..." },
    ...
  ]
}
```

Full transaction history (up to 1500 per agent) is in the paired transactions shard:
```jsonc
{
  "00a691c6": [ /* same tx shape, all of them */ ],
  "00a692f1": [ ... ],
  ...
}
```

## Client-side period derivation

`byQuarter` and `byMonth` are intentionally NOT precomputed. To answer "how did you do in Q3 2022" the client runs a ~5ms reducer over `recentTransactions` (or the lazy-fetched full list) filtering by `close_date` / `list_date` in range. Same for any custom range.

This keeps shards small and lets the UI support arbitrary agent-picked ranges without regenerating data.

## What v2 does NOT (yet) have

- Market-level aggregates (still in `/market/`)
- Brokerage aggregates (still in `/brokerage/`)
- Hub lookup index (still in `/hubs/`)
- These three remain in v1 paths; they're additive rollups, cheap to regenerate independently.

## Rebuild

```bash
python3 "Complete Agent Project/02-scripts/rebuild_v2_agents.py"
# Reads phoenix_listdate_historical.csv + tucson_listdate_historical.csv (~1.5 GB)
# Produces v2/agents/ + v2/transactions/ in ~3 minutes.
# Enriches license/email/phone from v1 career shards.
```
