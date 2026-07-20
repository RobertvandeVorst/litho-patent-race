"""
Stage 5 — export the dbt marts from warehouse/litho.duckdb to compact JSON for
the frontend, in frontend/public/data/.

All filing-year series respect dim_filing_year.is_complete (the 2005–2021 window).
Floats are rounded to 3 decimals; null values are dropped (keys omitted or 0).
Idempotent: safe to re-run after any dbt build.

Run:  python scripts/export_marts.py
"""
from __future__ import annotations
import json, os
from datetime import datetime, timezone
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "warehouse", "litho.duckdb")
OUT = os.path.join(ROOT, "frontend", "public", "data")
os.makedirs(OUT, exist_ok=True)
con = duckdb.connect(DB, read_only=True)

# scope constants (sourced from the model, not hardcoded guesses)
CUTOFF = con.execute("select max(filing_year) from dim_filing_year where is_complete").fetchone()[0]
WIN_LO = con.execute("select min(filing_year) from dim_filing_year where is_complete").fetchone()[0]
CENSORING = (
    f"Filing years are shown only for the complete window {WIN_LO}–{CUTOFF}: the corpus is a fixed "
    f"grant-year window (2005–2025), so filing years before {WIN_LO} are left-censored and after "
    f"{CUTOFF} right-censored (below 90% of median-year volume) and are excluded."
)

TOTAL = con.execute("select count(*) from fct_patent").fetchone()[0]


def r3(x):
    """Round to 3 decimals; None/NaN -> 0.0."""
    if x is None:
        return 0.0
    x = float(x)
    return 0.0 if x != x else round(x, 3)


def rows(sql, params=None):
    cur = con.execute(sql, params or [])
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def write(name, obj):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)
    size = os.path.getsize(path)
    print(f"  {name:32} {size:>7,} bytes")
    return size


print(f"Exporting to {OUT}  (complete window {WIN_LO}-{CUTOFF}, total {TOTAL:,})\n")
sizes = {}

# top-N player lists (by total patents, named only)
top15 = [r["player"] for r in rows(
    "select player from dim_player where player<>'Other' order by total_patents desc limit 15")]
top8 = top15[:8]

# ---------------------------------------------------------------- 1. kpis
named_players = con.execute("select count(*) from dim_player where player<>'Other'").fetchone()[0]
cov_pct = con.execute(
    "select round(100.0*count(*) filter(where player<>'Other')/count(*),3) from fct_patent").fetchone()[0]
grange = con.execute("select min(grant_date), max(grant_date) from fct_patent").fetchone()


def era_euv(lo, hi):
    r = con.execute(
        "select count(*) filter(where is_euv_any) e, count(*) n from fct_patent f "
        "join dim_filing_year d using(filing_year) where d.is_complete and filing_year between ? and ?",
        [lo, hi]).fetchone()
    return {"years": f"{lo}-{hi}", "patents": r[1], "euv_any": r[0],
            "euv_share_pct": r3(100.0 * r[0] / r[1]) if r[1] else 0.0}


kpis = {
    "total_patents": TOTAL,
    "grant_date_range": {"start": str(grange[0]), "end": str(grange[1])},
    "distinct_named_players": named_players,
    "coverage_pct": r3(cov_pct),
    "euv_share_early": era_euv(2005, 2010),
    "euv_share_late": era_euv(2015, 2021),
    "complete_filing_year_window": {"start": int(WIN_LO), "end": int(CUTOFF)},
    "censoring_note": CENSORING,
}
sizes["kpis.json"] = write("kpis.json", kpis)

# ---------------------------------------------------------------- 2. filings_by_player_year
# complete years only (mart already filters); top 15 players verbatim, the rest
# rolled into "Other named". Never includes the unmapped 'Other' bucket.
fpy = rows("""
    select filing_year,
           case when player in ({ph}) then player else 'Other named' end as player,
           sum(patents) as patents
    from mart_filings_by_player_year
    group by 1, 2
    having sum(patents) > 0
    order by filing_year, patents desc
""".format(ph=",".join("?" * len(top15))), top15)
fpy = [{"filing_year": int(r["filing_year"]), "player": r["player"], "patents": int(r["patents"])} for r in fpy]
sizes["filings_by_player_year.json"] = write("filings_by_player_year.json",
                                             {"window": {"start": int(WIN_LO), "end": int(CUTOFF)},
                                              "series": fpy})

# ---------------------------------------------------------------- 3. euv_share_by_year
overall = rows("""select filing_year, total_patents, euv_any, euv_any_share_pct
                  from mart_euv_share_by_year where scope='ALL' order by filing_year""")
overall = [{"filing_year": int(r["filing_year"]), "total": int(r["total_patents"]),
            "euv_any": int(r["euv_any"]), "euv_share_pct": r3(r["euv_any_share_pct"])} for r in overall]
# all-years series (incl. censored) so the time chart can DRAW the greyed censored
# ranges; each point carries is_complete. Trimmed to 2003+ (the pre-2003 tail is
# sparse and left-censored anyway).
overall_all = rows("""
    select f.filing_year, count(*) total, count(*) filter(where f.is_euv_any) euv_any, d.is_complete
    from fct_patent f join dim_filing_year d using(filing_year)
    where f.filing_year >= 2003
    group by f.filing_year, d.is_complete order by f.filing_year""")
overall_all = [{"filing_year": int(r["filing_year"]), "total": int(r["total"]),
                "euv_any": int(r["euv_any"]),
                "euv_share_pct": r3(100.0 * r["euv_any"] / r["total"]) if r["total"] else 0.0,
                "is_complete": bool(r["is_complete"])} for r in overall_all]
by_player = []
for p in top8:
    ser = rows("""select filing_year, total_patents, euv_any, euv_any_share_pct
                  from mart_euv_share_by_year where scope=? order by filing_year""", [p])
    by_player.append({"player": p, "series": [
        {"filing_year": int(r["filing_year"]), "total": int(r["total_patents"]),
         "euv_any": int(r["euv_any"]), "euv_share_pct": r3(r["euv_any_share_pct"])} for r in ser]})
sizes["euv_share_by_year.json"] = write("euv_share_by_year.json",
                                        {"window": {"start": int(WIN_LO), "end": int(CUTOFF)},
                                         "overall": overall, "overall_all": overall_all,
                                         "players": by_player})

# ---------------------------------------------------------------- 4. pivot (hero)
# top 8 by complete-window filing volume; EUV-any share early vs late + verdict.
pivot_players = [r["player"] for r in rows("""
    select f.player, count(*) n from fct_patent f join dim_filing_year d using(filing_year)
    where d.is_complete and f.player<>'Other' group by 1 order by n desc limit 8""")]


def player_era(p, lo, hi):
    r = con.execute(
        "select count(*) filter(where is_euv_any) e, count(*) n from fct_patent f "
        "join dim_filing_year d using(filing_year) where d.is_complete and f.player=? "
        "and filing_year between ? and ?", [p, lo, hi]).fetchone()
    return (r[1], (100.0 * r[0] / r[1]) if r[1] else 0.0)


def verdict(early, late):
    if late < early - 0.5:
        return "moved away"
    if late >= 2 * early and (late - early) >= 3:
        return "pivoted"
    return "flat"


pivot = []
for p in pivot_players:
    en, ep = player_era(p, 2005, 2010)
    ln, lp = player_era(p, 2015, 2021)
    pivot.append({"player": p, "early_years": "2005-2010", "late_years": "2015-2021",
                  "early_share_pct": r3(ep), "late_share_pct": r3(lp),
                  "early_n": en, "late_n": ln, "verdict": verdict(ep, lp)})
pivot.sort(key=lambda d: d["late_share_pct"], reverse=True)
sizes["pivot.json"] = write("pivot.json", {"players": pivot})

# ---------------------------------------------------------------- 5. leaderboard
# per-player EUV counts under BOTH flags (drives the Measurement toggle) + the
# corpus-wide agreement matrix for its side rail.
lb = rows("""
    select l.rank, l.player, d.player_category, l.player_country, l.total_patents,
           count(*) filter (where f.is_euv_title) as euv_title,
           count(*) filter (where f.is_euv_cpc)   as euv_cpc,
           count(*) filter (where f.is_euv_any)   as euv_any
    from mart_player_leaderboard l
    join dim_player d using(player)
    join fct_patent f on f.player = l.player
    group by l.rank, l.player, d.player_category, l.player_country, l.total_patents
    order by l.rank""")
leaderboard = []
for r in lb:
    tot = int(r["total_patents"]); euv = int(r["euv_any"])
    item = {"rank": int(r["rank"]), "player": r["player"],
            "player_category": r["player_category"], "total_patents": tot,
            "euv_title": int(r["euv_title"]), "euv_cpc": int(r["euv_cpc"]),
            "euv_any": euv, "euv_share_pct": r3(100.0 * euv / tot) if tot else 0.0}
    if r["player_country"]:                       # omit null country
        item["country"] = r["player_country"]
    leaderboard.append(item)
ag = con.execute("""select
        count(*) filter (where is_euv_title and is_euv_cpc)          as both,
        count(*) filter (where is_euv_title and not is_euv_cpc)      as title_only,
        count(*) filter (where is_euv_cpc and not is_euv_title)      as cpc_only,
        count(*) filter (where not is_euv_title and not is_euv_cpc)  as neither,
        count(*) filter (where is_euv_title)                         as title_total,
        count(*) filter (where is_euv_cpc)                           as cpc_total,
        count(*) filter (where is_euv_any)                           as any_total
    from fct_patent""").fetchone()
agreement = {"both": ag[0], "title_only": ag[1], "cpc_only": ag[2], "neither": ag[3],
             "title_total": ag[4], "cpc_total": ag[5], "any_total": ag[6]}
sizes["leaderboard.json"] = write("leaderboard.json",
                                  {"agreement": agreement, "players": leaderboard})

# ---------------------------------------------------------------- 6. subtech_network (matrix)
# A player x sub-technology matrix (heatmap). Rows = top 15 players by total,
# columns = every sub-tech bucket they appear in. Cells are the FULL (unpruned)
# per-patent primary counts, so each row sums to the player's total.
player_meta = {r["player"]: r for r in rows(
    "select player, player_category, total_patents from dim_player where player<>'Other'")}
cell_rows = rows("""
    select player, subtech, weight from mart_subtech_network
    where player in ({ph})
""".format(ph=",".join("?" * len(top15))), top15)
col_total = {}
by_pair = {}
for r in cell_rows:
    c = int(r["weight"])
    col_total[r["subtech"]] = col_total.get(r["subtech"], 0) + c
    by_pair[(r["player"], r["subtech"])] = c
subtechs = sorted(col_total, key=lambda s: -col_total[s])           # columns by total desc
mplayers = [{"player": p, "category": player_meta[p]["player_category"],
             "total": int(player_meta[p]["total_patents"])} for p in top15]  # top15 already total-desc
cells = [{"player": p, "subtech": s, "count": by_pair[(p, s)]}
         for p in top15 for s in subtechs if (p, s) in by_pair]
# sanity: each row's cells sum to that player's total
for mp in mplayers:
    rsum = sum(c["count"] for c in cells if c["player"] == mp["player"])
    assert rsum == mp["total"], f"row sum {rsum} != total {mp['total']} for {mp['player']}"
max_cell = max((c["count"] for c in cells), default=1)
print(f"    subtech_matrix: {len(mplayers)} players x {len(subtechs)} sub-techs, "
      f"{len(cells)} non-empty cells, max cell {max_cell}")
sizes["subtech_network.json"] = write("subtech_network.json", {
    "matrix": {"players": mplayers, "subtechs": subtechs, "cells": cells, "max_cell": max_cell},
})

# ---------------------------------------------------------------- 7. meta
meta = {
    "source": "PatentsView Granted Patent Disambiguated Data (PVGPATDIS), data.uspto.gov",
    "licence": "CC-BY 4.0",
    "cpc_scope": "CPC subclass G03F (microlithography), utility patents",
    "date_window": {"grant_start": 2005, "grant_end": 2025},
    "complete_filing_window": {"start": int(WIN_LO), "end": int(CUTOFF)},
    "censoring_rationale": CENSORING,
    "total_patents": TOTAL,
    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}
sizes["meta.json"] = write("meta.json", meta)

# ---------------------------------------------------------------- verify
total_bytes = sum(sizes.values())
print(f"\nTotal: {total_bytes:,} bytes ({total_bytes/1024:.1f} KiB)")
assert total_bytes < 1_048_576, f"exceeds 1 MB: {total_bytes}"

print("\nVerifying each file parses...")
for name in sizes:
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        json.load(f)
    print(f"  {name}: OK")

# leaderboard totals still sum to the named total
named_total = con.execute("select count(*) from fct_patent where player<>'Other'").fetchone()[0]
lb_sum = sum(p["total_patents"] for p in leaderboard)
assert lb_sum == named_total, f"leaderboard sum {lb_sum} != named {named_total}"
print(f"\nleaderboard total {lb_sum:,} == named total {named_total:,}  [PASS]")
con.close()
