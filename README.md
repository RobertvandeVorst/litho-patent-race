# The Shrinking Machine — the lithography patent race

An analytics-engineering portfolio project mapping two decades of the semiconductor
**lithography** patent race (CPC subclass `G03F`) from real USPTO / PatentsView data:
who files where, how the field shifted through the DUV→EUV inflection, and how the
key players (ASML, Canon, Nikon, Carl Zeiss, TSMC, Samsung, Intel, …) compete across
lithography sub-technologies.

## Stack

```
PatentsView bulk TSVs  →  DuckDB (raw)  →  dbt (staging → marts)  →  JSON  →  React + D3
```

- **DuckDB** — fast local warehouse; filters ~9M patents down to the G03F slice at load time.
- **dbt-duckdb** — layered models (staging → intermediate → marts), tests, docs/lineage.
- **React + D3** — interactive frontend (streamgraph, force-directed network, leaderboard, treemap).

## Data

Source: PatentsView "Granted Patent Disambiguated Data" (`PVGPATDIS`), CC-BY 4.0,
downloaded from the USPTO Open Data Portal Bulk Data Directory (data.uspto.gov).
Tables used: `g_patent`, `g_cpc_current`, `g_assignee_disambiguated`.

Raw data is **not** committed (multi-GB). Put the unzipped `.tsv` files in `data/raw/`.

## Quickstart

```bash
pip install -r requirements.txt

# 1. (sanity check) build the whole pipeline on the bundled synthetic sample
python scripts/load_duckdb.py --source data/sample
cd dbt/litho && dbt build --profiles-dir . && cd ../..

# 2. real data: unzip the three .tsv.zip into data/raw/, then
python scripts/load_duckdb.py --source data/raw
cd dbt/litho && dbt build --profiles-dir . && cd ../..

# 3. explore lineage
cd dbt/litho && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .
```

## Layout

```
scripts/
  generate_sample.py   synthetic data matching the PatentsView schema (for testing)
  load_duckdb.py       load + scope-filter the TSVs into DuckDB raw schema
dbt/litho/
  models/staging/      typed, cleaned 1:1 views over raw
  models/intermediate/ assignee→player normalization, primary player/sub-tech per patent
  models/marts/        fct_patent, dim_player, and pre-aggregated marts for the frontend
frontend/              React + D3 app (next step)
```
