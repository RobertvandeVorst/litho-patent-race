with src as (select * from {{ source('raw', 'patent') }}),

app as (
    -- one application row per patent (g_application is 1:1 on the in-scope set);
    -- if that ever changes, keep the earliest parseable filing_date.
    select
        patent_id::varchar                          as patent_id,
        min(try_cast(filing_date as date))          as filing_date_raw
    from {{ source('raw', 'application') }}
    group by patent_id
),

base as (
    select
        s.patent_id::varchar                                    as patent_id,
        try_cast(s.patent_date as date)                         as grant_date,
        s.patent_title                                          as title,
        try_cast(s.num_claims as int)                           as num_claims,
        a.filing_date_raw
    from src s
    left join app a on a.patent_id = s.patent_id::varchar
    where try_cast(s.patent_date as date) is not null
)

select
    patent_id,
    grant_date,
    extract(year from grant_date)::int                          as grant_year,
    title,
    num_claims,
    -- filing_date is trusted only if it parses, is on/before the grant date, and
    -- lands in 1990+ (g_application carries mangled years like 1074/1682 for some
    -- old patents); anything else becomes null rather than corrupting the time axis.
    case
        when filing_date_raw is not null
             and filing_date_raw <= grant_date
             and extract(year from filing_date_raw) >= 1990
        then filing_date_raw
    end                                                          as filing_date,
    case
        when filing_date_raw is not null
             and filing_date_raw <= grant_date
             and extract(year from filing_date_raw) >= 1990
        then extract(year from filing_date_raw)::int
    end                                                          as filing_year
from base
