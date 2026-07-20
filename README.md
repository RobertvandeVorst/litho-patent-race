# The Shrinking Machine — the lithography patent race

Two decades of the semiconductor **lithography** patent race, reconstructed from real
USPTO / PatentsView data. Every chip is printed by projecting circuit patterns onto silicon
with light; the race to use ever-shorter wavelengths — culminating in **extreme-ultraviolet
(EUV)** — is one of the defining contests in modern manufacturing. This project maps who
patented what across CPC subclass **`G03F`** (microlithography), 2005–2025, and asks a
sharp question: *who actually pivoted to EUV, and who did not?*

**Live demo:** _coming soon_ — <!-- VERCEL_URL --> (deploying to Vercel)

---

## The headline finding

Across the analytically complete window, **EUV's share of lithography filings roughly
tripled** — from ~**3.9%** of filings in 2005–2010 to ~**13.8%** in 2020–2021, peaking at
**14.7%** in 2021.

But the pivot was **concentrated, not universal**:

- **TSMC pivoted hardest** — EUV grew from **1.3%** of its filings (2005–2010) to **31.2%**
  (2015–2021).
- **Canon is the only retreat** — **2.0% → 0.4%**, staying with DUV / nanoimprint.
- **ASML — the company that builds the EUV scanners — looks flat** in this data. Its output
  stays majority non-EUV throughout, because ASML titles its patents generically
  ("lithographic apparatus") rather than "EUV". That surprise is what motivated the
  measurement-validity work below.

Of the 41,321 in-scope patents, **64.8% map to 31 canonical players** (ASML, TSMC, Canon,
Carl Zeiss, Samsung, Nikon, materials firms, chipmakers, metrology/EDA, mask suppliers).

---

## What this demonstrates

This is an analytics-engineering portfolio piece; the interesting parts are the
*engineering decisions*, not just the charts.

- **Scale handled at ingest.** The raw PatentsView tables are **~5.7 GB** of TSV. DuckDB
  scope-filters them to CPC `G03F` + utility + the grant-year window **at load time**, so the
  warehouse holds only the **41,321** patents that matter and everything downstream is fast.
- **Layered dbt modelling with tests and lineage.** Staging → intermediate → marts:
  typed 1:1 staging views, an assignee→player normalization map, one primary player and
  sub-technology per patent, then `fct_patent`, `dim_player`, `dim_filing_year` and
  pre-aggregated marts. dbt tests enforce not-null / uniqueness / accepted-values and a
  custom test that no `filing_year` predates the corpus.
- **Measurement validity — the core of the project.** "Is this an EUV patent?" has no
  ground-truth field, so two independent signals were built and cross-checked:
  - a **title-keyword flag** (`is_euv_title`) — which proved **biased**: it found only
    **108** EUV patents for ASML;
  - a **CPC-classification flag** (`is_euv_cpc`) — four EUV-specific classification codes,
    chosen by their overlap with the title flag (36–51% vs ~4–6% for general optics codes) —
    which found **339** for ASML;
  - the **union** (`is_euv_any`) is used as the fairest measure. The CPC flag surfaces
    **1,407** EUV patents the title alone misses, roughly doubling the corpus EUV count to
    **2,992** and correcting the anti-ASML bias.
- **Right-censoring handled honestly.** Because the corpus only contains patents *granted*
  by end-2025, recent filing years are incomplete. A `dim_filing_year` model flags a
  **complete window of 2005–2021**; every filing-year figure excludes censored years by
  default and the frontend draws them greyed-and-labelled rather than hiding the caveat.

---

## Limitations (read these before citing a number)

- **Grant lag.** Filing precedes grant by a median ~2.3–3.5 years, so filing-year series
  reflect R&D timing but depend on eventual grant.
- **Complete window 2005–2021.** Filing years after 2021 are right-censored (their
  slower-to-issue patents aren't granted yet) and before 2005 left-censored; both are
  excluded from trends.
- **US-only.** This is USPTO-granted data. Filings made only to the EPO/JPO/KIPO and never
  granted in the US are invisible — a partial view of a global race.
- **Primary-assignee attribution.** Each patent is credited to a single primary player and
  sub-technology (lowest sequence); co-assignees and secondary classifications are not
  counted in headline totals.
- **EUV is a proxy.** `is_euv_any` is the fairest available signal but still under-counts
  firms (notably ASML) whose EUV work is classified generically.

---

## Stack

```
PatentsView bulk TSVs  →  DuckDB (scope-filtered)  →  dbt (staging → marts)  →  JSON  →  React + D3
```

- **DuckDB** — fast local warehouse; filters ~5.7 GB down to the 41,321-patent G03F slice at load time.
- **dbt-duckdb** — layered models (staging → intermediate → marts), tests, docs/lineage.
- **React + D3** — editorial single-page frontend (slope chart, EUV-share time series,
  player × sub-technology heatmap, ranked leaderboard). D3 as the maths engine; React renders the SVG.

## Quickstart

The repo is runnable **without the bulk download** — a small synthetic sample ships in
`data/sample/` so the whole pipeline builds end-to-end.

```bash
pip install -r requirements.txt

# 1. build the pipeline on the bundled synthetic sample (no download needed)
python scripts/load_duckdb.py --source data/sample
cd dbt/litho && dbt build --profiles-dir . && cd ../..

# 2. real data: unzip the PatentsView .tsv files into data/raw/, then
python scripts/load_duckdb.py --source data/raw
cd dbt/litho && dbt build --profiles-dir . && cd ../..

# 3. export the marts to JSON for the frontend
python scripts/export_marts.py

# 4. run the frontend
cd frontend && npm install && npm run dev

# (optional) explore dbt lineage
cd dbt/litho && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .
```

## Data, source & licence

- **Source:** PatentsView "Granted Patent Disambiguated Data" (`PVGPATDIS`), downloaded from
  the **USPTO Open Data Portal** Bulk Data Directory (data.uspto.gov). Tables used:
  `g_patent`, `g_cpc_current`, `g_assignee_disambiguated`, `g_application`.
- **Licence:** **CC-BY 4.0** — attribution required. This is **not** public-domain data; any
  reuse must credit PatentsView / USPTO.
- The raw bulk TSVs (~5.7 GB) are **not** committed; unzip them into `data/raw/`. The
  DuckDB warehouse and generated reports are regenerable and also untracked.

## Layout

```
scripts/
  generate_sample.py   synthetic data matching the PatentsView schema (for testing)
  load_duckdb.py       load + scope-filter the TSVs into the DuckDB raw schema
  export_marts.py      read the dbt marts → frontend/public/data/*.json
  build_summary_report.py  Word report of the corpus (regenerable)
dbt/litho/
  models/staging/      typed, cleaned 1:1 views over raw
  models/intermediate/ assignee→player normalization, primary player/sub-tech per patent
  models/marts/        fct_patent, dim_player, dim_filing_year, and pre-aggregated marts
  tests/               custom data tests (e.g. filing-year validity)
frontend/
  src/                 React + D3 single-page app (reads public/data/*.json at runtime)
  public/data/         exported marts the app renders
```
