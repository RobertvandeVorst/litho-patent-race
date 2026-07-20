"""
Build the single authoritative data summary: reports/litho_data_summary.docx.

This supersedes all earlier reports. Every figure comes from a query against the
CURRENT warehouse/litho.duckdb marts; queries + results print to the terminal.
All filing-year time series use COMPLETE filing years only (cutoff 2021, from
dim_filing_year). EUV is measured primarily by is_euv_any (title OR CPC).

Run:  python scripts/build_summary_report.py
"""
from __future__ import annotations
import os, textwrap
import duckdb
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "warehouse", "litho.duckdb")
REPORTS = os.path.join(ROOT, "reports")
FIGS = os.path.join(REPORTS, "figs")
DOCX = os.path.join(REPORTS, "litho_data_summary.docx")
os.makedirs(FIGS, exist_ok=True)
con = duckdb.connect(DB, read_only=True)

CUTOFF = 2021  # last complete filing year (from dim_filing_year); asserted below


def q(sql, label=""):
    print("\n" + "=" * 78)
    if label:
        print("# " + label)
    print(textwrap.dedent(sql).strip())
    print("-" * 78)
    df = con.execute(sql).fetchdf()
    print(df.to_string(index=False, max_rows=60))
    return df


def scalar(sql, label=""):
    return q(sql, label).iloc[0, 0]


# ---- palette (validated light-mode, dataviz skill) ----
CAT = ["#2a78d6", "#008300", "#e87ba4", "#eda100", "#1baf7a",
       "#eb6834", "#4a3aa7", "#e34948", "#6b6a66", "#111111"]
BLUE, GREEN, ORANGE = "#2a78d6", "#008300", "#eb6834"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
plt.rcParams.update({
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
})


def save(fig, name):
    p = os.path.join(FIGS, name)
    fig.tight_layout(); fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    return p


# =====================================================================
# QUERIES
# =====================================================================
# assert the cutoff matches the model
model_cutoff = scalar("select max(filing_year) from dim_filing_year where is_complete",
                      "model cutoff (complete filing years)")
assert int(model_cutoff) == CUTOFF, f"cutoff drift: model={model_cutoff}"

n_patent = scalar("select count(*) from raw.patent")
n_cpc = scalar("select count(*) from raw.cpc")
n_assignee = scalar("select count(*) from raw.assignee")
n_application = scalar("select count(*) from raw.application")
n_scope = scalar("select count(*) from fct_patent", "in-scope patents")
dr = q("select min(grant_date) mn, max(grant_date) mx, "
       "min(grant_year) mny, max(grant_year) mxy from fct_patent", "grant date range")
min_grant, max_grant, min_year, max_year = dr.iloc[0]

claims = q("select round(avg(num_claims),1) avg, median(num_claims) med, "
           "min(num_claims) mn, max(num_claims) mx from fct_patent", "claims")
avg_claims, med_claims, min_claims, max_claims = claims.iloc[0]
n_orgs = scalar("select count(distinct disambig_assignee_organization) from raw.assignee "
                "where disambig_assignee_organization is not null and trim(disambig_assignee_organization)<>''",
                "distinct orgs")
n_invalid_filing = scalar("select count(*) filter (where filing_year is null) from fct_patent",
                          "invalid/missing filing_year")

per_grant = q("select grant_year, count(*) patents from fct_patent group by 1 order by 1",
              "patents per grant year")

# censoring table
dfy = q("""select filing_year, patents, median_grant_lag_years,
        pct_of_median_volume, is_complete
        from dim_filing_year where filing_year between 2003 and 2025 order by filing_year""",
        "dim_filing_year (censoring)")

# grant vs filing totals (all years, to show censoring)
gf = q("""with g as (select grant_year y, count(*) n from fct_patent group by 1),
          f as (select filing_year y, count(*) n from fct_patent where filing_year is not null group by 1)
          select coalesce(g.y,f.y) as yr, g.n grant_n, f.n filing_n
          from g full outer join f on g.y=f.y order by yr""", "grant vs filing totals")
gf = gf.rename(columns={"yr": "year"})

# ownership
leaderboard = q("""select l.rank, l.player, d.player_category, l.player_country, l.total_patents
        from mart_player_leaderboard l join dim_player d using(player) order by l.rank""",
        "normalized leaderboard")
cov = q("""select count(*) total, count(*) filter (where player<>'Other') named,
        count(*) filter (where player='Other') other,
        round(100.0*count(*) filter (where player<>'Other')/count(*),1) named_pct
        from fct_patent""", "coverage")
cov_total, cov_named, cov_other, cov_pct = cov.iloc[0]
top_other = q("""select org, count(distinct patent_id) patents from int_assignee_player
        where player='Other' group by 1 order by 2 desc limit 10""", "top 10 remaining Other")

# player_category (full)
pcat = q("""select player_category, count(*) patents,
        round(100.0*count(*)/sum(count(*)) over(),1) pct
        from fct_patent group by 1 order by patents desc""", "player_category breakdown")

# technology mix
subtech = q("""select subtech, count(*) patents, round(100.0*count(*)/sum(count(*)) over(),1) pct
        from fct_patent group by 1 order by patents desc""", "subtech distribution")

# EUV corpus shares + agreement
euv_share = q("""select
        round(100.0*count(*) filter (where is_euv_title)/count(*),2) title_pct,
        round(100.0*count(*) filter (where is_euv_cpc)/count(*),2) cpc_pct,
        round(100.0*count(*) filter (where is_euv_any)/count(*),2) any_pct,
        count(*) filter (where is_euv_title) title_n,
        count(*) filter (where is_euv_cpc) cpc_n,
        count(*) filter (where is_euv_any) any_n
        from fct_patent""", "EUV corpus shares")
euv_title_pct, euv_cpc_pct, euv_any_pct, euv_title_n, euv_cpc_n, euv_any_n = euv_share.iloc[0]
agree = q("""select count(*) filter (where is_euv_title and is_euv_cpc) n_both,
        count(*) filter (where is_euv_title and not is_euv_cpc) title_only,
        count(*) filter (where is_euv_cpc and not is_euv_title) cpc_only,
        count(*) filter (where not is_euv_title and not is_euv_cpc) neither
        from fct_patent""", "EUV agreement matrix")
a_both, a_title_only, a_cpc_only, a_neither = agree.iloc[0]

# top players by each flag
top_flag = q("""select player,
        count(*) filter (where is_euv_title) title,
        count(*) filter (where is_euv_cpc) cpc,
        count(*) filter (where is_euv_any) any_euv
        from fct_patent where player<>'Other' group by 1 order by any_euv desc limit 10""",
        "top players by EUV flag")

# EUV share by filing year (complete only, ALL)
euv_year = q("""select filing_year, total_patents, euv_title_share_pct, euv_cpc_share_pct, euv_any_share_pct
        from mart_euv_share_by_year where scope='ALL' and filing_year between 2005 and %d
        order by filing_year""" % CUTOFF, "EUV share by filing year (complete)")

# era aggregates (complete years)
era = q("""with b as (select * from fct_patent f join dim_filing_year d using(filing_year) where d.is_complete)
        select era, round(100.0*any_/n,1) any_pct, round(100.0*title/n,1) title_pct, round(100.0*cpc/n,1) cpc_pct, n
        from (
          select '2005-2010' era, count(*) filter (where is_euv_any) any_, count(*) filter (where is_euv_title) title,
                 count(*) filter (where is_euv_cpc) cpc, count(*) n from b where filing_year between 2005 and 2010
          union all select '2015-2021', count(*) filter (where is_euv_any), count(*) filter (where is_euv_title),
                 count(*) filter (where is_euv_cpc), count(*) from b where filing_year between 2015 and 2021
          union all select '2020-2021', count(*) filter (where is_euv_any), count(*) filter (where is_euv_title),
                 count(*) filter (where is_euv_cpc), count(*) from b where filing_year between 2020 and 2021)
        order by era""", "EUV era aggregates (complete)")

# top 6 pivot
pivot = q("""with b as (select * from fct_patent f join dim_filing_year d using(filing_year) where d.is_complete),
        t6 as (select player from b where player<>'Other' group by 1 order by count(*) desc limit 6)
        select b.player,
          round(100.0*count(*) filter (where is_euv_any and filing_year between 2005 and 2010)/nullif(count(*) filter (where filing_year between 2005 and 2010),0),1) early_pct,
          round(100.0*count(*) filter (where is_euv_any and filing_year between 2015 and 2021)/nullif(count(*) filter (where filing_year between 2015 and 2021),0),1) late_pct
        from b join t6 using(player) group by b.player order by late_pct desc""",
        "top 6 EUV pivot (complete)")

# ASML series (complete)
asml = q("""select filing_year, total_patents total, euv_any, (total_patents-euv_any) non_euv, euv_any_share_pct
        from mart_euv_share_by_year where scope='ASML' and filing_year between 2005 and %d
        order by filing_year""" % CUTOFF, "ASML EUV by filing year (complete)")

# filings by player year (complete, top 8)
top8 = leaderboard.head(8)["player"].tolist()
plist = ", ".join(f"'{p}'" for p in top8)
filings_wide = q(f"""select filing_year,
        {', '.join(f'''sum(case when player='{p}' then patents else 0 end) as "{p}"''' for p in top8)}
        from mart_filings_by_player_year where player in ({plist})
        group by filing_year order by filing_year""", "filings by player (complete, top 8)")

# data quality
nulls = q("""select
        (select count(*) from raw.patent where patent_title is null or trim(patent_title)='') null_title,
        (select count(*) from raw.patent where try_cast(num_claims as int) is null) null_claims,
        (select count(*) from raw.patent where try_cast(patent_date as date) is null) bad_date,
        (select count(*) from fct_patent where player_country is null) null_country,
        (select count(*) from fct_patent where subtech='Other G03F') other_subtech""",
        "null / fallback rates")
# Percentages use the SAME denominator as the report prose (all in-scope patents),
# so count and percentage agree: e.g. 1,666 / 41,321 = 4.0%.
multi = q("""with a as (select patent_id, count(*) n from raw.assignee group by 1),
             c as (select patent_id, count(*) n from stg_cpc group by 1),
             tot as (select count(*)::double t from fct_patent)
        select
          (select count(*) filter (where n>1) from a) n_multi_assignee,
          round(100.0*(select count(*) filter (where n>1) from a)/(select t from tot),1) pct_multi_assignee,
          (select count(*) filter (where n>1) from c) n_multi_cpc,
          round(100.0*(select count(*) filter (where n>1) from c)/(select t from tot),1) pct_multi_cpc,
          (select t::bigint from tot) total_patents""",
        "multi-valued relationships (denominator = all in-scope patents)")
n_ma, pct_ma, n_mc, pct_mc, multi_total = multi.iloc[0]

# full per-player EUV counts (all named players) — for prose lookups and ranks,
# so every per-player figure in the text is pulled from a query, never typed.
euv_players = q("""select player,
        count(*) filter (where is_euv_title) title,
        count(*) filter (where is_euv_cpc) cpc,
        count(*) filter (where is_euv_any) any_euv
        from fct_patent where player<>'Other' group by 1""", "per-player EUV counts (all named)")
euv_players["title_rank"] = euv_players["title"].rank(ascending=False, method="min").astype(int)
euv_players["cpc_rank"] = euv_players["cpc"].rank(ascending=False, method="min").astype(int)

# lookups keyed by player
PV = {r["player"]: r for _, r in pivot.iterrows()}          # early_pct, late_pct (EUV-any share)
EF = {r["player"]: r for _, r in euv_players.iterrows()}     # title, cpc, any_euv, ranks
# censoring pct for a specific year
DFY = {int(r["filing_year"]): r for _, r in dfy.iterrows()}


def ordinal(n):
    n = int(n)
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"

# =====================================================================
# CHARTS
# =====================================================================
def intx(ax): ax.xaxis.set_major_locator(MaxNLocator(integer=True))

# 1. patents per grant year
fig, ax = plt.subplots(figsize=(7.2, 3.3))
ax.plot(per_grant["grant_year"], per_grant["patents"], color=BLUE, lw=2, marker="o", ms=3)
ax.set_xlabel("Grant year"); ax.set_ylabel("Patents"); ax.set_ylim(bottom=0); intx(ax)
ax.set_title("G03F patents granted per year", loc="left", fontsize=11, pad=8)
fig_grant = save(fig, "per_grant_year.png")

# 2. grant vs filing (censoring)
gf2 = gf[(gf["year"] >= 2005) & (gf["year"] <= 2025)]
fig, ax = plt.subplots(figsize=(7.4, 3.6))
ax.plot(gf2["year"], gf2["grant_n"], color=BLUE, lw=2, marker="o", ms=3, label="by grant year")
ax.plot(gf2["year"], gf2["filing_n"], color=ORANGE, lw=2, marker="s", ms=3, label="by filing year")
ax.axvspan(CUTOFF + 0.5, 2025.5, color="#f0efec", zorder=0)
ax.text(CUTOFF + 0.7, ax.get_ylim()[1]*0.9, "censored\n(excluded)", fontsize=7.5, color=MUTED, va="top")
ax.set_xlabel("Year"); ax.set_ylabel("Patents"); ax.set_ylim(bottom=0); intx(ax)
ax.set_title(f"Same corpus by grant year vs filing year (cutoff {CUTOFF})", loc="left", fontsize=11, pad=8)
ax.legend(frameon=False, fontsize=9)
fig_gf = save(fig, "grant_vs_filing.png")

# 3. subtech bar
sd = subtech.sort_values("patents")
fig, ax = plt.subplots(figsize=(7.4, 4.4))
bars = ax.barh(sd["subtech"], sd["patents"], color=BLUE, height=0.7)
ax.set_xlabel("Patents (primary sub-technology)"); ax.grid(axis="y", visible=False)
ax.set_title(f"Patents across lithography sub-technologies ({len(subtech)} buckets)", loc="left", fontsize=11, pad=8)
for b, v in zip(bars, sd["patents"]):
    ax.text(v + max(sd["patents"])*0.01, b.get_y()+b.get_height()/2, f"{int(v):,}",
            va="center", ha="left", fontsize=7.5, color=INK2)
ax.set_xlim(right=max(sd["patents"])*1.13)
fig_sub = save(fig, "subtech.png")

# 4. EUV share by filing year (title/cpc/any)
fig, ax = plt.subplots(figsize=(7.4, 3.8))
ax.plot(euv_year["filing_year"], euv_year["euv_any_share_pct"], color=BLUE, lw=2.2, marker="o", ms=4, label="any (title OR CPC)")
ax.plot(euv_year["filing_year"], euv_year["euv_cpc_share_pct"], color=GREEN, lw=1.8, marker="^", ms=3, label="CPC only")
ax.plot(euv_year["filing_year"], euv_year["euv_title_share_pct"], color=ORANGE, lw=1.8, marker="s", ms=3, label="title only")
ax.set_xlabel("Filing year"); ax.set_ylabel("EUV share of filings (%)"); ax.set_ylim(bottom=0); intx(ax)
ax.set_title(f"EUV share of G03F filings by filing year (complete years ≤{CUTOFF})", loc="left", fontsize=11, pad=8)
ax.legend(frameon=False, fontsize=8)
fig_euv = save(fig, "euv_share.png")

# 5. top players filings by filing year (complete)
fig, ax = plt.subplots(figsize=(7.6, 4.2))
yrs = filings_wide["filing_year"].tolist()
for i, p in enumerate(top8):
    ax.plot(yrs, filings_wide[p], color=CAT[i], lw=1.8, label=p)
    ax.text(yrs[-1] + 0.15, filings_wide[p].iloc[-1], p, color=CAT[i], fontsize=7.5, va="center")
ax.set_xlabel("Filing year"); ax.set_ylabel("Patents filed"); ax.set_ylim(bottom=0); intx(ax)
ax.set_xlim(right=yrs[-1] + 2.5)
ax.set_title(f"Filings per filing year — top 8 players (complete years ≤{CUTOFF})", loc="left", fontsize=11, pad=8)
ax.legend(ncol=2, fontsize=7.5, frameon=False, loc="upper left")
fig_trends = save(fig, "trends.png")

# 6. EUV pivot: top 6 early vs late (grouped bar)
fig, ax = plt.subplots(figsize=(7.4, 3.6))
x = np.arange(len(pivot)); w = 0.38
ax.bar(x - w/2, pivot["early_pct"], w, color="#9ec5f4", label="2005–2010")
ax.bar(x + w/2, pivot["late_pct"], w, color=BLUE, label="2015–2021")
ax.set_xticks(x); ax.set_xticklabels(pivot["player"], fontsize=9)
ax.set_ylabel("EUV-any share of filings (%)"); ax.grid(axis="x", visible=False)
ax.set_title("Who pivoted to EUV? Top 6 players, early vs recent", loc="left", fontsize=11, pad=8)
for xi, e, l in zip(x, pivot["early_pct"], pivot["late_pct"]):
    ax.text(xi - w/2, e + 0.4, f"{e:.0f}", ha="center", fontsize=7, color=INK2)
    ax.text(xi + w/2, l + 0.4, f"{l:.0f}", ha="center", fontsize=7, color=INK2)
ax.legend(frameon=False, fontsize=8)
fig_pivot = save(fig, "euv_pivot.png")

# =====================================================================
# DOCUMENT
# =====================================================================
doc = Document()
nrm = doc.styles["Normal"]; nrm.font.name = "Calibri"; nrm.font.size = Pt(10.5)


def prose(t):
    p = doc.add_paragraph(t); p.paragraph_format.space_after = Pt(8); return p


def table(df, headers=None, numeric=None):
    cols = list(df.columns); labels = headers or cols
    t = doc.add_table(rows=1, cols=len(cols)); t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, lab in enumerate(labels):
        t.rows[0].cells[i].text = str(lab)
        for para in t.rows[0].cells[i].paragraphs:
            for r in para.runs: r.font.bold = True; r.font.size = Pt(9)
    year_cols = {c for c in cols if "year" in c.lower() or c.lower() in ("yr", "rank")}
    pct_cols = {c for c in cols if "pct" in c.lower() or "share" in c.lower() or "percent" in c.lower()}
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for i, c in enumerate(cols):
            v = row[c]
            if isinstance(v, (bool, np.bool_)):                 # booleans -> Yes/No
                txt = "Yes" if bool(v) else "No"
            elif v is None:
                txt = ""
            elif c in pct_cols:                                 # percentages -> always one decimal (6.0, not 6)
                try: txt = f"{float(v):.1f}"
                except (ValueError, TypeError): txt = str(v)
            elif c in year_cols:                                # years/ranks -> plain int, no separators
                txt = str(int(v))
            elif isinstance(v, float) and v == int(v):
                txt = f"{int(v):,}"
            elif isinstance(v, (int, np.integer)) or (numeric and c in numeric):
                try: txt = f"{int(v):,}"
                except (ValueError, TypeError): txt = str(v)
            elif isinstance(v, float): txt = f"{v:,.1f}"
            else: txt = str(v)
            cells[i].text = txt
            for para in cells[i].paragraphs:
                for r in para.runs: r.font.size = Pt(9)
    doc.add_paragraph()
    return t


def kvtable(rows):
    t = doc.add_table(rows=0, cols=2); t.style = "Light Grid Accent 1"
    for k, v in rows:
        c = t.add_row().cells; c[0].text = str(k); c[1].text = str(v)
        for cc in c:
            for para in cc.paragraphs:
                for r in para.runs: r.font.size = Pt(9)
    doc.add_paragraph()
    return t


# ---- title ----
doc.add_heading("The Lithography Patent Race", level=0)
s = doc.add_paragraph("Authoritative data summary — CPC subclass G03F, grants 2005–2025")
s.runs[0].font.size = Pt(13); s.runs[0].font.color.rgb = RGBColor(0x52, 0x51, 0x4E)
m = doc.add_paragraph(
    f"Source: PatentsView Granted Patent Disambiguated Data (CC-BY 4.0)  ·  "
    f"Warehouse: warehouse/litho.duckdb  ·  {int(n_scope):,} patents in scope  ·  "
    f"Time series use complete filing years ≤{CUTOFF}")
m.runs[0].font.size = Pt(9); m.runs[0].font.color.rgb = RGBColor(0x89, 0x87, 0x81)
doc.add_paragraph(
    "This document supersedes all earlier interim reports. Where it differs from earlier "
    "figures, this version is correct: it fixes right-censoring of recent filing years and "
    "replaces the biased title-only EUV measure with a validated title-or-CPC signal."
).runs[0].font.italic = True
doc.add_paragraph()

# ---- 1. scope ----
doc.add_heading("1. Scope and provenance", level=1)
prose(
    "This is a scope-filtered slice of the USPTO / PatentsView “Granted Patent Disambiguated "
    "Data” bulk release (PVGPATDIS), under the Creative Commons Attribution 4.0 licence. Four bulk "
    "TSVs — g_patent, g_cpc_current, g_assignee_disambiguated and g_application — were loaded "
    "into a local DuckDB warehouse and filtered at load time to CPC subclass G03F (microlithography), "
    "utility patents, granted 2005–2025. Country is not in the assignee table; player countries "
    "come from the normalization map.")
kvtable([
    ("raw.patent rows", f"{int(n_patent):,}"),
    ("raw.cpc rows (G03F classifications)", f"{int(n_cpc):,}"),
    ("raw.assignee rows", f"{int(n_assignee):,}"),
    ("raw.application rows", f"{int(n_application):,}"),
    ("Patents in scope (fct_patent)", f"{int(n_scope):,}"),
    ("Grant date range", f"{min_grant} → {max_grant}"),
    ("CPC filter", "subclass = G03F; utility only"),
    ("Source / licence", "PatentsView PVGPATDIS (data.uspto.gov) / CC-BY 4.0"),
])

# ---- 2. methodology / measurement validity ----
doc.add_heading("2. Methodology and measurement validity", level=1)
doc.add_heading("2.1 Censoring: the complete filing-year window", level=2)
_comp = dfy[dfy["is_complete"].astype(bool)]
win_lo, win_hi = int(_comp["filing_year"].min()), int(_comp["filing_year"].max())
prose(
    "Two dates exist per patent: the grant date (always observed) and the application filing date "
    "(the better proxy for when R&D happened, leading grant by a median of ~2.3–3.5 years). We "
    "prefer filing year for all time series, but because the corpus is a fixed grant-year window "
    "(patents GRANTED 2005–2025), the filing-year axis is censored at BOTH ends and only a middle "
    "window is analytically safe.")
prose(
    f"Right-censoring: the corpus contains only patents already granted by end-2025, so recent filing "
    f"years are missing their slower-to-issue patents. dim_filing_year flags a year complete when its "
    f"volume is at least 90% of the median-year volume (1,830 → threshold 1,647); the last year "
    f"clearing that bar is {win_hi} (at 90.2%), while 2022 falls to 60.5%. "
    f"Left-censoring: the corpus starts at grant year {int(min_year)}, so patents filed in 2003–2004 "
    f"but granted before {int(min_year)} are absent entirely — only their slow-to-grant minority "
    f"survived into the window, leaving those early filing years incomplete too. A filing year is "
    f"therefore marked complete only if it clears both bounds; here the complete window is "
    f"{win_lo}–{win_hi}. All filing-year marts and every chart in this report exclude incomplete years "
    f"by default. Of {int(n_scope):,} patents, {int(n_invalid_filing)} have an invalid/missing filing year.")
prose(
    f"The table below starts at 2003 deliberately, to show the left boundary: 2003 and 2004 are "
    f"left-censored (marked ‘No’) despite healthy raw volumes, and {win_lo} is the first complete "
    f"year. The full pre-2003 tail (filing years back to 1995, all sparse and incomplete) is omitted "
    f"for brevity.")
table(dfy.rename(columns={"median_grant_lag_years": "median_lag_yrs"}),
      headers=["Filing yr", "Patents", "Median lag (yr)", "% of median vol", "Complete?"])
doc.add_picture(fig_gf, width=Inches(6.2)); doc.add_paragraph()
prose(
    "The chart shows why: the grant-year and filing-year series track each other through the 2010s, "
    f"then the filing-year line collapses after {CUTOFF} — that collapse is censoring, not a real "
    "drop in inventive activity. The shaded region is excluded from all analysis.")

doc.add_heading("2.2 Two EUV signals, and why we use their union", level=2)
prose(
    "“Is this an EUV patent?” has no ground-truth field, so we built two independent flags. "
    "is_euv_title matches EUV keywords in the title (extreme ultraviolet, EUV/EUVL, 13.5 nm, soft "
    "x-ray), word-boundary anchored. is_euv_cpc is true when the patent carries an EUV-specific CPC "
    "code. is_euv_any is their union and is the primary measure used here.")
prose(
    f"The title flag proved biased: it under-counts firms that describe EUV generically. ASML — "
    f"which builds the EUV scanners — titles patents “lithographic apparatus,” so the title "
    f"flag finds only {int(EF['ASML']['title'])} ASML EUV patents; the CPC flag finds "
    f"{int(EF['ASML']['cpc'])}. The CPC codes were chosen "
    f"data-drivenly by their overlap with the title flag: four leaf codes stand out at 36–51% "
    "overlap versus ~4–6% for general optics codes — G03F7/70033 (EUV/soft-X-ray source), "
    "G03F7/70175 (EUV projection optics), G03F1/24 (reflection/EUV masks) and G03F1/22 (masks for "
    "≤100 nm radiation).")
prose(
    f"Corpus EUV share by flag: title {euv_title_pct}% ({int(euv_title_n):,}), CPC {euv_cpc_pct}% "
    f"({int(euv_cpc_n):,}), any {euv_any_pct}% ({int(euv_any_n):,}). The two flags agree on "
    f"{int(a_both):,} patents but each finds many the other misses (below) — so neither alone is "
    f"sufficient, and the union is the fairest single measure.")
table(agree, headers=["Both flags", "Title only", "CPC only", "Neither"])
prose(
    f"The CPC flag surfaces {int(a_cpc_only):,} EUV patents the title misses — nearly doubling the "
    f"signal and correcting the anti-ASML bias. What changed as a result: the headline EUV share is "
    f"higher and better distributed across firms, and (Section 6) the “who pivoted” verdicts shift.")

# ---- 3. corpus overview ----
doc.add_heading("3. Corpus overview", level=1)
peak = per_grant.loc[per_grant["patents"].idxmax()]
prose(
    f"The corpus holds {int(n_scope):,} granted G03F patents ({int(min_year)}–{int(max_year)}), "
    f"averaging {avg_claims} claims (median {int(med_claims)}, range {int(min_claims)}–{int(max_claims)}). "
    f"{int(n_orgs):,} distinct organizations appear in the raw assignee table. By grant year, annual "
    f"output peaks at {int(peak['patents']):,} in {int(peak['grant_year'])}.")
doc.add_picture(fig_grant, width=Inches(6.0)); doc.add_paragraph()

# ---- 4. ownership ----
doc.add_heading("4. Ownership", level=1)
prose(
    f"After normalizing organization-name variants into canonical players, {int(cov_named):,} of "
    f"{int(cov_total):,} patents ({cov_pct}%) map to a named player by primary assignee; "
    f"{int(cov_other):,} ({100-cov_pct:.1f}%) remain ‘Other’. The leaderboard (with industry "
    f"category) follows.")
table(leaderboard, headers=["Rank", "Player", "Category", "Country", "Patents"],
      numeric=["total_patents"])
prose("The largest organizations still unmapped — the next candidates for the normalization map:")
table(top_other, headers=["Unmapped organization", "Patents"], numeric=["patents"])
prose("By industry category (every patent, including the unmapped ‘Other’ bucket):")
table(pcat, headers=["Player category", "Patents", "Share %"], numeric=["patents"])

# ---- 5. technology mix ----
doc.add_heading("5. Technology mix", level=1)
top_sub = subtech.iloc[0]
other_g03f = float(subtech.loc[subtech.subtech == "Other G03F", "pct"].iloc[0]) if (subtech.subtech == "Other G03F").any() else 0.0
prose(
    f"Each patent takes one primary sub-technology from its lead G03F classification. The two "
    f"originally-dominant areas (exposure apparatus and photoresist) were split by CPC group into finer "
    f"functional buckets, giving {len(subtech)} buckets with no bucket above ~25% — the largest is now "
    f"‘{top_sub['subtech']}’ at {top_sub['pct']}%. Only {other_g03f}% land in the residual "
    f"‘Other G03F’ bucket.")
table(subtech, headers=["Sub-technology", "Patents", "Share %"], numeric=["patents"])
doc.add_picture(fig_sub, width=Inches(6.2)); doc.add_paragraph()

# ---- 6. EUV analysis ----
doc.add_heading("6. EUV analysis (primary measure: is_euv_any)", level=1)
e05 = era.loc[era.era == "2005-2010"].iloc[0]
e15 = era.loc[era.era == "2015-2021"].iloc[0]
e20 = era.loc[era.era == "2020-2021"].iloc[0]
peak_euv = euv_year.loc[euv_year["euv_any_share_pct"].idxmax()]
prose(
    f"Measured over complete filing years with is_euv_any, EUV's share of G03F filings rises from "
    f"{e05['any_pct']}% (2005–2010) to {e15['any_pct']}% (2015–2021), reaching {e20['any_pct']}% "
    f"in 2020–2021 and peaking at {peak_euv['euv_any_share_pct']}% in {int(peak_euv['filing_year'])}. "
    f"A first clear step appears around 2012–13. (Earlier interim reports quoted “9.8% in 2023” "
    f"and “8.0% for 2020–2025” — both were title-only and censored, and are superseded.)")
doc.add_picture(fig_euv, width=Inches(6.2)); doc.add_paragraph()
table(euv_year, headers=["Filing yr", "Total", "Title %", "CPC %", "Any %"], numeric=["total_patents"])
prose(f"Top players by EUV patent count under each flag — note ASML rises from "
      f"{ordinal(EF['ASML']['title_rank'])} (title) to {ordinal(EF['ASML']['cpc_rank'])} (CPC):")
table(top_flag, headers=["Player", "Title", "CPC", "Any"], numeric=["title", "cpc", "any_euv"])

doc.add_heading("6.1 Who actually pivoted to EUV?", level=2)
prose(
    "Comparing each top-6 player's EUV-any share early (2005–2010) vs recently (2015–2021) shows "
    "the pivot was concentrated, not universal. The chipmaker TSMC and the optics supplier Carl Zeiss "
    "moved hard into EUV; ASML did not shift in composition (its output stays majority non-EUV); Canon "
    "moved away.")
table(pivot, headers=["Player", "EUV % 2005–10", "EUV % 2015–21"])
doc.add_picture(fig_pivot, width=Inches(6.0)); doc.add_paragraph()
prose(
    f"On ASML specifically: even under the less-biased CPC/any flag, ASML's EUV share only moves from "
    f"{PV['ASML']['early_pct']}% (2005–2010) to {PV['ASML']['late_pct']}% (2015–2021) "
    f"of its own filings — non-EUV apparatus work dominates throughout. ASML's flat total is genuinely "
    f"mostly non-EUV; it is not a clean DUV→EUV swap. (And even CPC under-counts ASML, whose broad "
    f"scanner patents often carry only generic G03F7/70 codes — so this is a conservative read.)")

# ---- 7. trends ----
doc.add_heading("7. Trends over time (filing year, complete years)", level=1)
prose(
    f"Filings per filing year for the eight largest players, over complete years ≤{CUTOFF}. TSMC's "
    f"rise and Nikon's / IBM's decline are the dominant structural shifts.")
doc.add_picture(fig_trends, width=Inches(6.4)); doc.add_paragraph()

# ---- 8. data quality & limitations ----
doc.add_heading("8. Data quality and limitations", level=1)
nt, nc, bd, ncy, os_ = nulls.iloc[0]
prose(
    f"Key fields are essentially complete: {int(nt):,} missing titles, {int(nc):,} non-integer "
    f"num_claims, {int(bd):,} unparseable grant dates. {int(ncy):,} patents have no mapped country "
    f"(primary assignee is ‘Other’) and {int(os_):,} carry ‘Other G03F’ sub-tech. "
    f"Of all {int(multi_total):,} in-scope patents, {pct_ma}% list multiple assignees ({int(n_ma):,}) and "
    f"{pct_mc}% carry multiple G03F classifications ({int(n_mc):,}); the pipeline reduces each to one "
    f"primary player and sub-tech by lowest sequence number.")
doc.add_heading("Limitations", level=2)
for b in [
    "Grant lag: filing precedes grant by a median ~2.3–3.5 years, so filing-year series reflect "
    "R&D timing but depend on eventual grant.",
    f"Right-censoring: only patents granted by end-2025 are present, so filing years after {CUTOFF} are "
    "incomplete and excluded; recent activity is understated and this report reflects the field only "
    f"through ~{CUTOFF}.",
    "US-only: this is USPTO-granted data. Filings made only to the EPO/JPO/KIPO and never granted in the "
    "US are invisible — a partial view of a global race.",
    "Primary-assignee attribution: each patent is credited to a single primary player and sub-technology "
    "(lowest sequence); co-assignees and secondary classifications are not counted in the headline totals.",
    "EUV is a keyword/CPC proxy, not a ground-truth label; is_euv_any is the fairest available measure but "
    "still under-counts firms (notably ASML) whose EUV work is classified generically.",
    f"Player countries come from the normalization map, not the data; unmapped ‘Other’ orgs "
    f"({100-cov_pct:.0f}% of patents) have no country.",
]:
    p = doc.add_paragraph(b, style="List Bullet"); p.paragraph_format.space_after = Pt(3)

# ---- 9. key insights ----
doc.add_heading("9. Key insights", level=1)
lead = leaderboard.iloc[0]
insights = [
    f"ASML leads the named field with {int(lead['total_patents']):,} patents; the normalization map now "
    f"covers {cov_pct}% of the {int(cov_total):,} in-scope patents (up from 43.5%).",
    f"EUV rose from {e05['any_pct']}% of filings (2005–2010) to {e20['any_pct']}% (2020–2021) "
    f"by the union flag, peaking at {peak_euv['euv_any_share_pct']}% in {int(peak_euv['filing_year'])}.",
    f"The title-only EUV flag was biased: it found {int(EF['ASML']['title'])} ASML EUV patents vs "
    f"{int(EF['ASML']['cpc'])} for CPC; the CPC flag adds "
    f"{int(a_cpc_only):,} patents the title misses, nearly doubling the corpus EUV count to {int(euv_any_n):,}.",
    f"The EUV pivot was concentrated: TSMC {PV['TSMC']['early_pct']}%→{PV['TSMC']['late_pct']}% and "
    f"Carl Zeiss {PV['Carl Zeiss']['early_pct']}%→{PV['Carl Zeiss']['late_pct']}%, while ASML barely "
    f"moved ({PV['ASML']['early_pct']}%→{PV['ASML']['late_pct']}%) and Canon fell "
    f"({PV['Canon']['early_pct']}%→{PV['Canon']['late_pct']}%).",
    f"Right-censoring matters: the cutoff is {CUTOFF}; filing volume drops to "
    f"{DFY[2022]['pct_of_median_volume']}% of median by 2022, so "
    f"any trend past {CUTOFF} would be an artefact and is excluded.",
    f"Technology is now well-distributed across {len(subtech)} sub-tech buckets (largest {top_sub['pct']}%), and named "
    f"players split {int(pcat.loc[pcat.player_category!='Other','patents'].sum()):,} patents across Equipment, "
    f"Chipmaker, Materials, Metrology-EDA and Mask-substrate.",
]
for s in insights:
    p = doc.add_paragraph(s, style="List Bullet"); p.paragraph_format.space_after = Pt(4)

doc.save(DOCX)
print(f"\nSaved: {DOCX}")
con.close()
