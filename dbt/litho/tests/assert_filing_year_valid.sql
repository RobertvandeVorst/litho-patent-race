-- fct_patent.filing_year must be null (invalid/missing) or >= 1990.
-- Any row with a filing_year below 1990 means the stg_patent guard leaked a
-- corrupt date; this test returns those offending rows so dbt fails.
select patent_id, filing_year
from {{ ref('fct_patent') }}
where filing_year is not null
  and filing_year < 1990
