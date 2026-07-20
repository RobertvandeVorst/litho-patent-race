-- Filings per player per FILING year. Censored (incomplete) filing years are
-- excluded via dim_filing_year.is_complete, so the series is analytically safe by
-- default (cutoff currently 2021 — see dim_filing_year). Patents with no valid
-- filing_year are also excluded.
select
    f.filing_year,
    f.player,
    count(*) as patents
from {{ ref('fct_patent') }} f
join {{ ref('dim_filing_year') }} d
  on d.filing_year = f.filing_year and d.is_complete
where f.player <> 'Other'
group by f.filing_year, f.player
order by f.filing_year, f.player
