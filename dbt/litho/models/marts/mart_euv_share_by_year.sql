-- EUV filings per filing year for the whole corpus (scope='ALL') and each of the
-- top 8 named players. Three EUV signals are reported side by side: title-based,
-- CPC-based, and their union (any). Censored filing years are excluded via
-- dim_filing_year.is_complete (cutoff currently 2021), so shares are not distorted
-- by right-censoring.

with base as (
    select f.filing_year, f.player, f.is_euv_title, f.is_euv_cpc, f.is_euv_any
    from {{ ref('fct_patent') }} f
    join {{ ref('dim_filing_year') }} d
      on d.filing_year = f.filing_year and d.is_complete
),

top8 as (
    select player
    from base
    where player <> 'Other'
    group by player
    order by count(*) desc
    limit 8
),

overall as (
    select
        filing_year,
        'ALL'                                  as scope,
        count(*)                               as total_patents,
        count(*) filter (where is_euv_title)   as euv_title,
        count(*) filter (where is_euv_cpc)     as euv_cpc,
        count(*) filter (where is_euv_any)     as euv_any
    from base
    group by filing_year
),

by_player as (
    select
        b.filing_year,
        b.player                               as scope,
        count(*)                               as total_patents,
        count(*) filter (where b.is_euv_title) as euv_title,
        count(*) filter (where b.is_euv_cpc)   as euv_cpc,
        count(*) filter (where b.is_euv_any)   as euv_any
    from base b
    join top8 t on t.player = b.player
    group by b.filing_year, b.player
)

select
    filing_year,
    scope,
    total_patents,
    euv_title,
    euv_cpc,
    euv_any,
    round(100.0 * euv_title / nullif(total_patents, 0), 1) as euv_title_share_pct,
    round(100.0 * euv_cpc   / nullif(total_patents, 0), 1) as euv_cpc_share_pct,
    round(100.0 * euv_any   / nullif(total_patents, 0), 1) as euv_any_share_pct
from (select * from overall union all select * from by_player)
order by scope, filing_year
