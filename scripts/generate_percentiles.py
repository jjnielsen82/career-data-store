#!/usr/bin/env python3
"""
Generate v2/percentiles/{market}.json — per-period quantile grids of agent
production, used by the career dashboard for TRUE period-specific percentile
ranks ("Top 4% in Q2 2026") and the anonymized next-rung ladder.

Reads:  ~/career-data-store/v2/transactions/{market}/*.json  (token -> [tx,...])
Writes: ~/career-data-store/v2/percentiles/{market}.json

Periods: "career", every calendar year with closed deals, and quarters
("YYYY-qN") for the current and previous year.

Per period, per metric (volume, deals):
  n  — number of agents with >=1 closed deal in the period (the universe)
  q  — 101 quantile values (value at percentile 0..100, ascending)
  t  — 9 tail quantile values (percentile 99.1 .. 99.9, for Top-1% precision)

Client lookup: percentile(v) = interpolate v against q (and t above p99).

Safe to re-run any time; deterministic for closed periods. Called at the end
of rebuild_v2_agents.py so it refreshes with every full rebuild.
"""
import json
import sys
from datetime import date
from pathlib import Path

STORE = Path.home() / "career-data-store"
MARKETS = ["phoenix", "tucson"]


def quantile_grid(values):
    """values: unsorted list of numbers -> (101-pt grid, 9-pt tail grid)."""
    vs = sorted(values)
    n = len(vs)
    if n == 0:
        return [], []
    def at(pct):  # linear-interpolated value at percentile pct (0..100)
        idx = pct / 100.0 * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return vs[lo] * (1 - frac) + vs[hi] * frac
    grid = [round(at(p)) for p in range(101)]
    tail = [round(at(99.0 + i / 10.0)) for i in range(1, 10)]
    return grid, tail


def build_market(market):
    tx_dir = STORE / "v2" / "transactions" / market
    shards = sorted(tx_dir.glob("*.json"))
    if not shards:
        print(f"  !! no transaction shards for {market}, skipping")
        return None

    today = date.today()
    q_years = {str(today.year), str(today.year - 1)}

    # period -> {"volume": [...], "deals": [...]}  (one entry per active agent)
    periods = {}

    def bucket(key, vol, deals):
        p = periods.setdefault(key, {"volume": [], "deals": []})
        p["volume"].append(vol)
        p["deals"].append(deals)

    for shard_path in shards:
        with open(shard_path) as f:
            shard = json.load(f)
        for token, txs in shard.items():
            # per-agent aggregates for this shard pass
            agg = {}  # period key -> [vol, deals]
            career = [0.0, 0]
            for t in txs:
                if t.get("status") != "Closed":
                    continue
                cd = t.get("close_date") or ""
                if len(cd) < 7:
                    continue
                price = t.get("soldPrice") or 0
                career[0] += price
                career[1] += 1
                yr = cd[:4]
                a = agg.setdefault(yr, [0.0, 0])
                a[0] += price
                a[1] += 1
                if yr in q_years:
                    qn = (int(cd[5:7]) - 1) // 3 + 1
                    qa = agg.setdefault(f"{yr}-q{qn}", [0.0, 0])
                    qa[0] += price
                    qa[1] += 1
            if career[1] == 0:
                continue
            bucket("career", career[0], career[1])
            for key, (v, d) in agg.items():
                bucket(key, v, d)

    out = {
        "schemaVersion": 1,
        "market": market,
        "generatedAt": today.isoformat(),
        "periods": {},
    }
    for key, data in sorted(periods.items()):
        n = len(data["deals"])
        if n < 25:  # too small a universe to rank meaningfully
            continue
        vq, vt = quantile_grid(data["volume"])
        dq, dt = quantile_grid(data["deals"])
        out["periods"][key] = {
            "n": n,
            "volume": {"q": vq, "t": vt},
            "deals": {"q": dq, "t": dt},
        }
    return out


def main():
    out_dir = STORE / "v2" / "percentiles"
    out_dir.mkdir(parents=True, exist_ok=True)
    for market in MARKETS:
        print(f"building percentiles for {market}...")
        data = build_market(market)
        if data is None:
            continue
        dest = out_dir / f"{market}.json"
        with open(dest, "w") as f:
            json.dump(data, f, separators=(",", ":"))
        kb = dest.stat().st_size / 1024
        print(f"  wrote {dest} ({kb:.0f} KB, {len(data['periods'])} periods)")


if __name__ == "__main__":
    sys.exit(main())
