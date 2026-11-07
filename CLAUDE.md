# career-data-store

**Status:** LIVE data store (GitHub jjnielsen82/career-data-store)
**What it does:** Holds every data shard served by the agent career dashboards at elite.listerpros.com. Covers Phoenix (ARMLS) and Tucson (TARMLS): per-agent lifetime closings, year-by-year volume, city rankings, brokerage/office history, listings-taken stats, and hub lookup indexes. Agents reach their dashboard via a tokenized URL (token = `md5("{name}|{market}|career")[:8]`).
**How it's built/updated:** Rebuilt automatically (hourly) by the elite-orchestrator daemon on the Mac Studio from the MLS feeds plus `data/manual/manual_closings_{phoenix,tucson}.csv`. The orchestrator's Step 3c merges the manual closings on every cycle so they survive each rebuild. `v2/meta/generated.json` records the last build time and source CSVs.
**Key files:**
- `v2/agents/{market}/{prefix}.json` — meta shards (stats, period selector, 20-tx preview)
- `v2/transactions/{market}/{prefix}.json` — full per-agent tx history, lazy-fetched
- `v2/meta/generated.json`, `v2/meta/token_overrides.json`
- `v2/README.md` — full schema and design notes
- `data/manual/manual_closings_{phoenix,tucson}.csv` — the ONLY supported way to inject/correct deals
- v1 paths still live and read by current dashboards: `phoenix/`, `tucson/`, `market/`, `brokerage/`, `hubs/`, `listings_phoenix/`, `listings_tucson/`
**Services/deps:** elite-orchestrator (writer), elite.listerpros.com (reader), GitHub remote
**Gotchas:**
- Do NOT hand-edit the v2 shards (or any v1 shard) directly. Manual edits get overwritten on the next hourly rebuild. Route every correction through `manual_closings_{market}.csv`.
- This repo is data only. When deploying, only update data files, never touch dashboard HTML or design (that lives in the dashboard/site repo).
- Two-file-per-shard split (meta vs transactions) is deliberate for fast first paint; keep it.
- On a list/close price gap, credit the close price.
- Watch revenue math: a legacy cents bug inflated figures by ~60% (true 2026 YTD is about $931,000, not $1.46M). Verify any aggregate that looks too high.
