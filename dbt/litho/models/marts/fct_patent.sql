with joined as (
    select
        p.patent_id,
        p.grant_date,
        p.grant_year,
        p.filing_date,
        p.filing_year,
        p.title,
        p.num_claims,
        coalesce(a.player, 'Other')            as player,
        a.player_country,
        coalesce(a.player_category, 'Other')   as player_category,
        coalesce(a.subtech, 'Other G03F')      as subtech,
        -- title-based EUV signal: word-boundary anchored so 'euv' never matches
        -- inside an unrelated token; 'euvl?' also catches the 'EUVL' acronym.
        regexp_matches(
            lower(coalesce(p.title, '')),
            '(\beuvl?\b|extreme ultraviolet|13\.5\s*nm|soft x-?ray)'
        )                                      as is_euv_title,
        -- CPC-based EUV signal (independent of the title wording)
        coalesce(a.is_euv_cpc, false)          as is_euv_cpc
    from {{ ref('stg_patent') }} p
    left join {{ ref('int_patent_attributes') }} a using (patent_id)
)

select
    *,
    (is_euv_title or is_euv_cpc) as is_euv_any
from joined
