-- Censoring guard for the filing-year axis. A filing year is "complete" only if it
-- is free of BOTH censoring effects:
--   * Right-censoring: the corpus holds only patents GRANTED by end-2025, so recent
--     filing years are missing their slower-to-issue patents. Cutoff = the LAST year
--     whose volume is still >= 90% of the median-year volume.
--   * Left-censoring: the corpus starts at GRANT year 2005, so patents filed before
--     2005 but granted before 2005 are absent entirely. Any filing year earlier than
--     the first in-scope grant year is therefore incomplete (only its slow-to-grant
--     patents survived into the window).
-- Every filing-year mart filters on is_complete so neither effect contaminates a trend.

with base as (
    select filing_year,
           date_diff('day', filing_date, grant_date) as lag_days
    from {{ ref('fct_patent') }}
    where filing_year is not null
),

y as (
    select
        filing_year,
        count(*)                        as patents,
        median(lag_days)                as median_grant_lag_days
    from base
    group by filing_year
),

m as (select median(patents) as median_year_volume from y),

-- lower bound: the first grant year in scope (patents filed before this are left-censored)
bounds as (select min(grant_year) as grant_window_start from {{ ref('fct_patent') }}),

-- upper bound: last filing year still at >= 90% of the median-year volume
cutoff as (
    select max(y.filing_year) as cutoff_year
    from y cross join m
    where y.patents >= 0.9 * m.median_year_volume
)

select
    y.filing_year,
    y.patents,
    y.median_grant_lag_days,
    round(y.median_grant_lag_days / 365.25, 2)          as median_grant_lag_years,
    round(100.0 * y.patents / m.median_year_volume, 1)  as pct_of_median_volume,
    (y.filing_year >= (select grant_window_start from bounds)
     and y.filing_year <= (select cutoff_year from cutoff)) as is_complete
from y cross join m
order by y.filing_year
