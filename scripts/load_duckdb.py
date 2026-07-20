"""
Load the three PatentsView TSVs into DuckDB, filtered to scope at load time.

Usage:
    python scripts/load_duckdb.py --source data/sample          # test on synthetic data
    python scripts/load_duckdb.py --source /path/to/unzipped    # real data
    python scripts/load_duckdb.py --source data/raw --subclass G03F --start 2005 --end 2025

Filtering to G03F + date window here (rather than in dbt) keeps the warehouse small:
~9M patents collapse to the ~tens-of-thousands that matter, so everything downstream is fast.
Reading is streamed by DuckDB, so the full-size TSVs never need to fit in memory.
"""
import argparse
from pathlib import Path
import duckdb

ap = argparse.ArgumentParser()
ap.add_argument("--source", default="data/sample", help="folder containing the unzipped .tsv files")
ap.add_argument("--db", default="warehouse/litho.duckdb")
ap.add_argument("--subclass", default="G03F")
ap.add_argument("--start", type=int, default=2005)
ap.add_argument("--end", type=int, default=2025)
args = ap.parse_args()

root = Path(__file__).resolve().parents[1]
src = (root / args.source).resolve()
db_path = (root / args.db).resolve()
db_path.parent.mkdir(parents=True, exist_ok=True)

def tsv(name):
    p = src / name
    if not p.exists():
        raise SystemExit(f"missing file: {p}\n(unzip the .tsv.zip files into {src} first)")
    # quote='' disables quote handling (PatentsView TSVs use raw tabs, occasional stray quotes);
    # all_varchar keeps ingestion robust — typing happens in dbt staging.
    return (f"read_csv('{p.as_posix()}', delim='\\t', header=true, quote='\"', escape='\"', "
            f"nullstr='', ignore_errors=true, all_varchar=true)")

con = duckdb.connect(str(db_path))
con.execute("CREATE SCHEMA IF NOT EXISTS raw;")

# 1) scope set: patents whose *current* CPC includes the target subclass
con.execute(f"""
CREATE OR REPLACE TABLE raw.cpc AS
SELECT patent_id, cpc_sequence, cpc_section, cpc_class, cpc_subclass, cpc_group, cpc_type
FROM {tsv('g_cpc_current.tsv')}
WHERE patent_id IN (
    SELECT patent_id FROM {tsv('g_cpc_current.tsv')} WHERE cpc_subclass = '{args.subclass}'
);
""")

# 2) patents in scope + date window
con.execute(f"""
CREATE OR REPLACE TABLE raw.patent AS
SELECT p.patent_id, p.patent_type, p.patent_date, p.patent_title, p.num_claims
FROM {tsv('g_patent.tsv')} p
WHERE p.patent_id IN (SELECT DISTINCT patent_id FROM raw.cpc)
  AND p.patent_type = 'utility'
  AND (p.withdrawn IS NULL OR p.withdrawn IN ('0','false','False',''))
  AND TRY_CAST(p.patent_date AS DATE) BETWEEN DATE '{args.start}-01-01' AND DATE '{args.end}-12-31';
""")

# keep cpc + assignee restricted to the final in-window patent set
con.execute("""
CREATE OR REPLACE TABLE raw.cpc AS
SELECT c.* FROM raw.cpc c WHERE c.patent_id IN (SELECT patent_id FROM raw.patent);
""")

con.execute(f"""
CREATE OR REPLACE TABLE raw.assignee AS
SELECT a.patent_id, a.assignee_sequence, a.assignee_id,
       a.disambig_assignee_organization, a.assignee_type, a.location_id
FROM {tsv('g_assignee_disambiguated.tsv')} a
WHERE a.patent_id IN (SELECT patent_id FROM raw.patent);
""")

# application dates (filing_date) — restricted to the in-scope patent set.
# g_application.tsv is optional (the synthetic sample doesn't ship it): when the
# file is absent, create an empty raw.application so downstream models still build.
# filing_date is validated (corrupt/out-of-range values dropped) in stg_patent, not here.
app_file = src / "g_application.tsv"
if app_file.exists():
    con.execute(f"""
    CREATE OR REPLACE TABLE raw.application AS
    SELECT a.application_id, a.patent_id, a.patent_application_type,
           a.filing_date, a.series_code, a.rule_47_flag
    FROM {tsv('g_application.tsv')} a
    WHERE a.patent_id IN (SELECT patent_id FROM raw.patent);
    """)
else:
    con.execute("""
    CREATE OR REPLACE TABLE raw.application (
        application_id VARCHAR, patent_id VARCHAR, patent_application_type VARCHAR,
        filing_date VARCHAR, series_code VARCHAR, rule_47_flag VARCHAR
    );
    """)
    print("note: g_application.tsv not found -> raw.application created empty")

n_pat = con.execute("SELECT COUNT(*) FROM raw.patent").fetchone()[0]
n_cpc = con.execute("SELECT COUNT(*) FROM raw.cpc").fetchone()[0]
n_asg = con.execute("SELECT COUNT(*) FROM raw.assignee").fetchone()[0]
n_app = con.execute("SELECT COUNT(*) FROM raw.application").fetchone()[0]
yr = con.execute("SELECT MIN(patent_date), MAX(patent_date) FROM raw.patent").fetchone()
print(f"raw.patent      {n_pat:>7}   ({yr[0]} .. {yr[1]})")
print(f"raw.cpc         {n_cpc:>7}")
print(f"raw.assignee    {n_asg:>7}")
print(f"raw.application {n_app:>7}")
con.close()
print(f"warehouse: {db_path}")
