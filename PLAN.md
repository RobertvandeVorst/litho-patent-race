# Build plan — The Shrinking Machine (lithography patent race)

Working doc for continuing this project (ideally in **Claude Code**, run from the repo root).
Check off tasks as you go. Keep the whole build inside the ~10-hour budget: prefer the
simplest thing that ships each stage; note enhancements but don't gold-plate.

## Known facts (confirmed from the real data — don't re-derive)

- Data path (Windows): `C:\projects\semiconductor patent\` containing the unzipped TSVs
  `g_patent.tsv` (~1.1 GB), `g_assignee_disambiguated.tsv` (~1.1 GB), `g_cpc_current.tsv` (~3.3 GB).
- Confirmed columns:
  - `g_patent`: patent_id, patent_type, patent_date, patent_title, wipo_kind, num_claims, withdrawn, filename
  - `g_cpc_current`: patent_id, cpc_sequence, cpc_section, cpc_class, cpc_subclass, cpc_group, cpc_type
    - `cpc_group` format is concatenated, no space: e.g. `A63C9/001` → so G03F looks like `G03F7/70`.
  - `g_assignee_disambiguated`: patent_id, assignee_sequence, assignee_id,
    disambig_assignee_individual_name_first, disambig_assignee_individual_name_last,
    disambig_assignee_organization, assignee_type, **location_id** (NO country column here).
- Country is NOT in the assignee table. Players' countries come from the normalization map in
  `int_assignee_player`. (Optional enhancement: download `g_location.tsv`, join on `location_id`
  to get real countries for the long tail.)
- Scope: CPC subclass `G03F`, grant years 2005–2025.

## Stack

`PatentsView bulk TSVs → DuckDB (raw, scope-filtered) → dbt (staging → intermediate → marts) → JSON → React + D3`

---

## Stage 0 — Setup ✅ DONE
- Repo scaffold, requirements, .gitignore, synthetic sample generator.

## Stage 1 — Ingest + scope-filter ✅ DONE (verified on sample; real run pending)
- `scripts/load_duckdb.py` filters to G03F + 2005–2025 at load time.
- ⏭ Run on real data: `python scripts/load_duckdb.py --source "C:\projects\semiconductor patent"`
  - Acceptance: `raw.patent` lands somewhere in the ~15k–60k range; min/max grant dates inside window.

## Stage 2 — dbt staging ✅ DONE
- `stg_patent`, `stg_cpc` (with sub-tech mapping), `stg_assignee`.

## Stage 3 — Normalization + marts ✅ DONE (19 dbt nodes pass on sample)
- `int_assignee_player` (org → canonical player + country), `int_patent_attributes`.
- `fct_patent`, `dim_player`, `mart_filings_by_player_year`, `mart_player_leaderboard`, `mart_subtech_network`.

## Stage 4 — Real-data validation + tuning ✅ DONE
- [x] Run Stage 1 + `dbt build` on the real data. 41,321 in-scope patents (2005–2025).
- [x] Coverage check + normalization extension. See Stage 4b below.
- [x] Sub-tech check + refinement. See Stage 4b below.
- [x] EUV inflection: NOT visible in ASML grant counts (flat ~210–290/yr). Made visible via
      a title-based `is_euv` flag + filing-year axis (Stage 4b).
- Acceptance met: leaderboard credible (ASML #1 at 4,794), named coverage now 64.8%, 15
  balanced sub-tech buckets (max 18.4%).

## Stage 4b — Model improvement from the summary-report findings ✅ DONE
Report: `reports/litho_data_summary.docx` (original), `reports/stage4b_findings.docx` (this stage).

1. **Filing dates.** `g_application.tsv` loaded as `raw.application` (1:1 with patents on the
   in-scope set). `filing_date`/`filing_year` added to `stg_patent` + `fct_patent`, kept
   alongside `grant_year`. Validation: `TRY_CAST`, and valid only if `filing_date <= grant_date`
   AND `filing_year >= 1990` (else null). On the in-scope set **0 of 41,321** are invalid/missing
   (the mangled years like 1074/1682 belong to out-of-scope 1970s patents). `mart_filings_by_player_year`
   re-keyed on `filing_year`. dbt singular test `assert_filing_year_valid` guards `filing_year >= 1990`.
   - Finding: by grant year the corpus peaks in 2014; by filing year it peaks in **2004** and the
     recent years fall away (right-censoring — recent filings not yet granted). Filing year leads
     grant year by several years and is the better R&D-timing axis.

2. **EUV flag.** `is_euv` boolean on `fct_patent` from title keywords (`extreme ultraviolet`,
   `EUV`/`EUVL`, `13.5 nm`, `soft x-ray`), word-boundary anchored (`\b`), kept separate from the
   subtech bucket. New mart `mart_euv_share_by_year` (EUV vs non-EUV per filing year, overall + top 8).
   - ⚠️ **SUPERSEDED by Stage 4c.** These Stage 4b EUV figures were (a) title-only — a biased
     signal that under-counts ASML — and (b) contaminated by right-censored recent filing years.
     The specific claims "first step ~2013 (5.7%)", "~8–10% by 2021–2023", and "9.8% in 2023" are
     replaced by the CPC-augmented, complete-years figures below. Renamed `is_euv` → `is_euv_title`.

3. **Normalization coverage.** `int_assignee_player` extended with 19 orgs (Shin-Etsu, FUJIFILM,
   Tokyo Ohka, JSR, Rohm & Haas, Sumitomo Chemical, Nissan Chemical, Toshiba, Micron, SK Hynix,
   GlobalFoundries, BOE, Winbond, Infineon, Fujitsu, KLA-Tencor, Synopsys, Hoya, Molecular Imprints),
   with look-alike guards (Micron≠Micronic/Unimicron, Sumitomo Chemical≠Electric/Heavy, Rohm&Haas≠Rohm Co).
   Added `player_category` (Equipment / Materials / Chipmaker / Metrology-EDA / Mask-substrate / Other)
   to `int_assignee_player` → `fct_patent` + `dim_player`, with `not_null` + `accepted_values` tests.
   - Finding: named-player coverage **43.5% → 64.8%**. Remaining `Other` long tail: Kodak, LG Chem,
     Dai Nippon Printing, AMD, DuPont, NuFlare, LG Display, 3M, Lam Research, TI (next candidates).

4. **Sub-tech refinement.** Split the two oversized buckets via `cpc_group` in `stg_cpc`:
   Exposure apparatus (G03F7/70) → 5 functional buckets; Photoresist/process (rest of G03F7) → 4.
   - Finding: **15 buckets, max now 18.4%** (Photoresist compositions, was 36.5%); none above 25%;
     `Other G03F` still negligible (0.1%, 38 patents).

## Stage 4c — Methodological fixes (right-censoring + unbiased EUV signal) ✅ DONE

1. **Right-censoring.** The corpus holds only patents GRANTED by end-2025, so recent filing years
   are incomplete. New model **`dim_filing_year`** (per year: volume, median grant lag, % of
   median-year volume, `is_complete`). Median grant lag is ~2.3–3.5 yr. Cutoff rule: last filing
   year with ≥90% of the median-year volume (median volume 1,830 → threshold 1,647).
   - **Cutoff = 2021** (1,650 = 90.2%; 2022 falls to 60.5%). `is_complete` true for ≤2021.
   - **`mart_filings_by_player_year` and `mart_euv_share_by_year` now exclude censored years by
     default** (inner-join `dim_filing_year` on `is_complete`).

2. **Second, unbiased EUV signal (CPC-based).** Title flag renamed `is_euv_title`. Added
   **`is_euv_cpc`** = patent carries an EUV-specific CPC leaf code, chosen data-drivenly by
   title-overlap validation: **G03F7/70033** (EUV/soft-X-ray source, 51% title-overlap),
   **G03F7/70175** (EUV projection optics, 49%), **G03F1/24** (reflection/EUV masks, 43%),
   **G03F1/22** (masks for ≤100 nm radiation, 36%) — vs ~4–6% for general optics codes.
   Added **`is_euv_any`** = title OR cpc. `not_null` tests on all three.
   - Corpus share: title **3.84%** (1,585), cpc **6.02%** (2,489), any **7.24%** (2,992).
   - Agreement matrix: both 1,082 · title-only 503 · **cpc-only 1,407** · neither 38,329. The CPC
     flag surfaces 1,407 EUV patents the title misses (e.g. ASML 108→339).

3. **Corrected EUV trend (complete years only, `is_euv_any`).** Share rises **3.9% (2005–2010) →
   10.3% (2015–2021) → 13.8% (2020–2021)**; per-year peaks at 14.7% in 2021. First clear step ~2012–13
   (6.9–9.4% any). These replace the Stage 4b censored/title figures.

4. **ASML re-tested.** Even under the CPC/any flag, ASML's EUV share only rises **6.0% (2005–2010) →
   8.6% (2015–2021)** — non-EUV filings dominate throughout (1,410 → 1,493). **The composition-shift
   hypothesis does NOT hold for ASML**: its flat total is genuinely mostly non-EUV work, not a clean
   DUV→EUV swap (and even CPC under-counts ASML's generically-classified scanner patents). The firms
   that actually pivoted: **TSMC 1.3%→31.2%**, Carl Zeiss 7.9%→19.4%, Samsung 5.2%→14.3%; Nikon flat
   (3.2%→3.9%), Canon declined (2.0%→0.4%).

## Stage 5 — Export marts → JSON ✅ DONE
- [x] `scripts/export_marts.py`: reads the marts from DuckDB, writes 7 files to
      `frontend/public/data/` — `kpis`, `pivot`, `leaderboard`, `euv_share_by_year`,
      `filings_by_player_year`, `subtech_network`, `meta`. Floats rounded to 3 dp, no nulls.
- [x] Network pruned to top 15 players, links below weight 15 dropped (144 links, no orphans).
- [x] Every filing-year series respects `dim_filing_year.is_complete` (2005–2021).
- [x] `leaderboard.json` carries per-player `euv_title`/`euv_cpc` + the agreement matrix (drives §2).
- [x] `euv_share_by_year.json` carries `overall_all` (2003–2025 w/ `is_complete`) so the time
      chart can draw the censored years greyed.
- Acceptance met: 7 files, **46 KiB total** (<1 MB), all parse; leaderboard sums to named total
  (26,777); idempotent re-run; self-verifying (`assert`s in the script).

## Stage 6 — Frontend (React + D3) ✅ DONE
Vite + React in `frontend/`. D3 (`d3-scale`, `d3-shape`, `d3-force`, `d3-array`) as maths only;
React renders all SVG. **Every number comes from the JSON at runtime — nothing hardcoded**
(grep-verified). Design spec followed exactly (palette, Archivo/Space-Mono type, editorial masthead,
numbered sections, mono figure captions over hairlines).
- [x] §1 Hero — slope chart from `pivot.json`, coloured by verdict (pivoted indigo / flat muted /
      retreated umber), left-to-right stroke-dash draw-in, de-collided right labels w/ leader lines;
      ruled KPI rail from `kpis.json`.
- [x] §2 Measurement — title/CPC flag toggle; rows reorder with a FLIP transition; per-row rank-delta
      chip (ASML 4→2, Zeiss 2→5, Hoya surfaces at 3→114); agreement side rail.
- [x] §3 Field over time — true annual EUV-share line by filing year; pre-2005 + 2022–2025 drawn grey
      and labelled left-/right-censored.
- [x] §4 "Who competes where" — **heatmap matrix** (replaced the force-directed network, which was
      too dense at 29 nodes / 144 links to read). Rows = top 15 players by total desc; columns = the
      15 sub-tech buckets; cells shaded on a ground→EUV-indigo sequential ramp by patent count (empty
      cells unfilled with a hairline); full row names in Space Mono, rotated column labels with full
      name in `title`, a row-total column, a stepped legend, and per-cell hover (player/sub-tech/count).
      Fills full content width; on ≤720px it scrolls horizontally with the row-label column sticky.
      New `matrix` block added to `subtech_network.json` (unpruned; each row sums to the player total).
- [x] Contrast fix — Materials category colour darkened `#c79a3a → #8c6518` (was 1.71:1 on the ground,
      now 3.49:1); the `Other` fallback darkened to `#7a6b45` (3.46:1). All five categories now clear
      WCAG 3:1. No element renders with an undefined fallback colour (verified).
- [x] Methods footer from `meta.json` — CC-BY 4.0 (attribution required, **not** public domain),
      CPC scope, 2005–2021 window + why.
- Quality: responsive to 390px (near-square charts, tickers + tables keep full names); every SVG has
      `role="img"` + `<title>`/`<desc>`; `prefers-reduced-motion` disables draw-in & reordering;
      keyboard-operable toggle with visible focus; figures numbered 1–3 with no gaps.
- Verified: `npm run build` clean; SSR smoke test renders **41,321** from `kpis.json`; dev server
      serves app + all 7 data files (HTTP 200).
- Run: `cd frontend && npm install && npm run dev`.

## Stage 6b — Frontend polish ✅ DONE
Verified in headless Chrome (puppeteer-core) at 1280px and 390px.
1. **Matrix column labels.** Rendered as an **SVG header block** with explicit geometry (replacing the
   CSS-transform approach, which rotated the wrong way into the cells): each label is `text-anchor=start`
   at `(cx, H)` with `rotate(-45, cx, H)`, so it extends up-and-right and never crosses the grid's top
   edge. `H` is computed from the longest label measured via `getComputedTextLength()` (re-measured on
   `fonts.ready`); columns fill the content width with a reserved right-pad for the last label's reach.
   Verified programmatically at 1280px and 390px: **0 labels overlap** — lowest label bottom 561/759 vs
   grid top 580/778 ("Alignment/registration"); longest "Exp: projection/immersion" (168px) also clears.
   Also fixed: the §4 "what to look for" callout split "KLA-Tencor" across a line at the hyphen — now a
   non-breaking hyphen (U+2011).
2. **Line-chart labels.** Censored-band boundaries moved to the true midpoints (`x(win.start-0.5)`,
   `x(win.end+0.5)`); LEFT-CENSORED now sits vertically inside the band, clear of the y-axis; y-ticks
   deduped + min-spaced so the top pair never collides.
3. **Real hover/focus tooltips** (shared `Tooltip`, ground fill / ink border / mono / square):
   matrix cell → player, sub-tech, count, **share of row total** + row/column highlight; line →
   crosshair snapping to nearest year with share, EUV count, total; slope → player, early, recent,
   **Δ pp**. All marks are keyboard-focusable and announce the same content via `aria-label`
   (verified: focus tips fire, e.g. "2003 · censored · 4.9% · 93 EUV · 1,909"). Fixed a pointer-events
   issue where the transparent overlay wasn't capturing (`pointerEvents:'all'`).
4. **Storytelling & navigation.** (nav reworked in Stage 6d — see below.)
   c) Per-section "what to look for" notes, every number interpolated from JSON (TSMC 1.3%→31.2% /
      Canon 2.0%→0.4%; step 9.4% at 2013 → 14.7% at 2021; ASML 1,501 / 31.3% of its row, KLA 52.6%).
   d) Collapsible "+ method" disclosures on §2 (why two EUV flags — cites 1,407 cpc-only) and §3
      (what censoring means), collapsed by default.
- No horizontal overflow at 390px or 1280px (scrollWidth == innerWidth); page renders 41,321 at both.

## Stage 6d — Single left-rail navigation ✅ DONE
Replaced the sticky top nav and the four per-section "next" buttons with one `SideRail` so navigation
lives in exactly one place (old `SectionNav` + `.next` removed).
- **Fixed left rail**, anchored near the top (top:40px, matching the masthead's top padding, so the
  first entry lines up with the masthead rule) and positioned relative to the content column's left
  edge — its right edge sits ~24-28px to the left of the column, so it reads as attached rather than
  floating. Never overlaps the content (verified: railRight ≤ contentLeft at 1600/1280/1100px). Falls
  back to `position:absolute` (scrolls with the page) when the viewport is too short (max-height 560px).
  One entry per section + Methods: a square marker plus "N · NAME" in Space-Mono uppercase.
- Active marker **filled indigo**, label full-ink; inactive markers hairline outlines with muted
  labels. Active state transitions with a colour fade (no sliding).
- A thin vertical connecting line runs through the markers; the portion **above the active marker is
  indigo**, so the rail doubles as a reading-progress bar (progress height = activeIndex × item).
- A **Next ↓ / Top ↑** control below the last entry (becomes Top ↑ on the final section). Bottom-of-page
  detection makes Methods active even though the short footer can't reach the observer's mid-band.
- Driven by the existing IntersectionObserver scroll-spy; entries are real `<button>`s, tab-navigable,
  with visible focus and `aria-current="true"` on the active one; smooth-scroll normally, instant jump
  under `prefers-reduced-motion`.
- Responsive: labels at ≥1540px (first width where the ~150px labelled rail clears the column with a
  gap); **markers-only** at 720–1539px hugging the left edge; **compact sticky top bar** below 720px
  (a fixed rail is wrong on mobile).
- Verified in headless Chrome at 1600/1280/1100/390px: no horizontal overflow anywhere; the rail's
  right edge never reaches the content (e.g. 1280px: rail right 23 vs content left 90); labels only at
  ≥1500px; active/aria-current/click-scroll/Top all correct.

## Stage 6e — Polish & narrative pass ✅ DONE
1. **Measure & width.** Prose blocks widened 60→68ch (standfirst, lede, look, method); figures,
   tables and the matrix all span the full content column — the page alternates narrow prose / wide data.
2. **Key findings block** (new `KeyFindings`, between hero and §1): 4 ruled rows, every number
   interpolated from JSON (EUV grew 3.8× to a 14.7% peak; TSMC 1.3→31.2% vs Canon 2.0→0.4%; ASML 4th→2nd
   by flag; 64.8% mapped to 31 players). Each row links to the section that evidences it.
3. **Figure sources** removed from figure captions; a "Figure sources" list added to the methods footer
   (Fig 1 → pivot.json, etc).
4. **"What to look for" icon** — a hand-drawn inline SVG eye (1.5px stroke, currentColor, 15px) before
   the mono label; reads as a printer's mark.
5. **Scroll reveal** — `useReveal` hook: `[data-reveal]` elements fade-up (14px/420ms, stagger 60ms) via
   IntersectionObserver at 15%, once each; charts draw in on reveal (`useInViewOnce` drives the slope /
   line draw-in). Progressive enhancement: the hide is gated behind a JS-added `.js-reveal` class so
   content is visible without the enhancement; under `prefers-reduced-motion` the class is never added
   and everything renders immediately. Verified: 8 above-fold elements revealed on load, below-fold
   hidden until scrolled to; reduced-motion adds no class and hides nothing.
6. **Section 2** — the stray agreement panel replaced by a full-width horizontal **stacked bar** above
   the (now full-width) leaderboard: title-only 503·16.8% (muted) · both 1,082·36.2% (indigo) · CPC-only
   1,407·47% (lighter indigo, widest = the argument), with the explanatory sentence beneath.
7. Verified in headless Chrome: no horizontal overflow at 1600/1280/390px; no hardcoded data figures in
   `src/`; build clean; reduced-motion path renders everything immediately.

## Stage 6f — Four fixes ✅ DONE
1. **Masthead** eyebrow → "Robert van de Vorst · An analytics-engineering field study" (same mono
   uppercase treatment + rules).
2. **Key findings** — the whole row is now a full-width `<a>` (in-page link); hover/focus give a panel
   tint + indigo left rule; the "See ↓" affordance stays visible; real focus ring, keyboard-operable.
3. **Fig 1 player filter** — a wrapping row of mono chips (All + each pivot.json player, real buttons,
   `aria-pressed`). Selecting one keeps that line full-opacity and drops the others to a faint 0.13
   hairline (kept for context) with their labels faded out; "All" restores. 250ms transition, instant
   under reduced-motion. Chips wrap to 3 rows at 390px with no overflow.
4. **Section 2 bars** — leaderboard row regridded to `28px / name / 1fr bar / count / chip`; the bar
   column is now the dominant element (~64% of the row, 16px tall) and is scaled to the active flag's
   max so the top player's bar fills it. At 390px the bar shrinks (~132px) but never vanishes; the
   rank-delta chip drops instead.
- Verified in headless Chrome: no horizontal overflow at 1600/1280/390px; build clean; no hardcoded
  figures in src/.

## Stage 6g — Deploy polish (live) ✅ DONE
- **Live:** https://litho-patent-race.vercel.app/ (README placeholder filled in).
- **Glyph fix.** Space Mono / Archivo lack arrow & shape glyphs (→ ↓ ↑ ▲ ▼), so they rendered as
  missing-glyph boxes. Appended symbol fallbacks (`'Segoe UI Symbol', 'Apple Symbols',
  'Noto Sans Symbols2'`) to both `--font-mono` and `--font-display` so those chars fall back
  per-glyph. Also changed the Key Findings pivot to read "1.3% to 31.2%" (headline robustness).
  Verified in-browser: chips (▲ ■ →), rail (NEXT ↓ / TOP ↑), methods pipeline, and "SEE ↓" all render.
- **Narrower content column.** `--maxw` 1180 → **1040px** so the labelled left rail appears at common
  laptop widths. Recomputed the rail breakpoint: **labels from 1400px** (was 1540px); markers-only
  720–1399px; top bar <720px. Verified: no overlap with the content column at any width; no horizontal
  overflow at 1600/1440/1280/390px. Fig 3 matrix stays legible (41px cells at the narrower column —
  not cramped, so no bleed needed); fig 1 right-hand labels still clear.
- **Accessibility widget** floating at the right edge is **not from our code** (no such element in
  `src/`; the only `position:fixed` elements are the tooltip and the left rail) — it's a browser
  extension or the Vercel toolbar, so nothing to remove.

## Stage 6h — Rail labels at laptop widths ✅ DONE
The 1400px label threshold was still too high for scaled Windows laptops (innerWidth often 1280–1366;
one report at 990). Changed the constraint from "rail fits entirely outside the 1040px column box" to
"rail never overlaps actual content" — the rail may now sit over the page's left gutter/margin.
- Rail's right edge anchored to the content's left edge via `right: calc(50vw + 496px)` — a constant
  **16px gap** to the nearest text/figure at every width (checked against real element left edges, not
  the column box).
- **Label threshold lowered to 1200px**; labels **abbreviated** (Pivot / Measure / Time / Field /
  Methods) at 10px so the rail fits without clipping. Markers-only 720–1199px; top bar <720px.
- Verified: labels visible at 1200/1280/1366/1440/1600; gap = 16px at all; no content overlap; no
  horizontal overflow; rail not clipped at the left edge (railLeft ≥ 5px at 1200).

## Stage 6i — One always-labelled nav (top bar + rail) ✅ DONE
Removed the markers-only rail state entirely; navigation is labelled at every width.
- **<1200px: sticky top bar with FULL section names.** Centred with comfortable spacing from 720px up
  (padding/gap tuned so the five full names fit the content width at exactly 720px — 640/640, no
  clip/scroll); horizontal-scroll fallback on mobile.
- **≥1200px: fixed left rail with abbreviated labels** (right-edge anchored 16px left of content).
- The top-bar↔rail switch is at **1200px, not the requested 1040px**, because at ≤1040px the 1040px
  column fills the viewport with only a 40px gutter — a labelled rail there would overlap the headings
  (which the no-overlap rule forbids), and widening the gutter was ruled out. The rail needs ~160px of
  margin, which first appears at ~1200px. Below that the top bar (full names) is the labelled nav — so
  a 990px laptop now gets the full-name top bar, not markers.
- `title` + `aria-label` (full "N · Name") added to every rail item, rail marker, and top-bar item.
- Verified at 390/720/990/1024/1040/1200/1440px: a labelled nav renders at each, no content overlap
  (rail gap 16px), no horizontal overflow. Nav per width: 390/720/990/1024/1040 → top bar; 1200/1440 → rail.

## Stage 7 — Deploy + writeup ⏭
- [ ] Deploy to Vercel or GitHub Pages.
- [ ] README case-study: the question, the stack, the pipeline, the findings, screenshots.
- [ ] `dbt docs generate` — include the lineage graph as an artifact.

## Nice-to-haves (only if budget remains)
- Citation influence: add `g_us_patent_citation` (~2.25 GB) → `fct_citation` edge list, size nodes by citations.
- Real assignee countries via `g_location` join.
- A `dbt exposure` pointing at the deployed app.
