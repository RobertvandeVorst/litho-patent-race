with src as (select * from {{ source('raw', 'cpc') }})

select
    patent_id::varchar                  as patent_id,
    try_cast(cpc_sequence as int)       as cpc_sequence,
    cpc_subclass                        as cpc_subclass,
    cpc_group                           as cpc_group,
    cpc_type                            as cpc_type,
    -- Lithography sub-technology areas. The two dominant CPC areas — the exposure
    -- apparatus (G03F7/70) and photoresist compositions/processing (rest of G03F7) —
    -- are split into finer functional buckets so no single bucket dominates. The
    -- band labels track the G03F7/70.. and G03F7/.. subgroup structure and are
    -- approximate at group boundaries.
    case
        -- masks / reticles
        when cpc_group ilike 'G03F1/24%' or cpc_group ilike '%euv%' then 'EUV masks'
        when cpc_group ilike 'G03F1/%'                        then 'Masks / reticles'

        -- exposure apparatus (G03F7/70) — split by function
        when cpc_group ilike 'G03F7/700%' or cpc_group ilike 'G03F7/701%'
                                                              then 'Exposure: illumination & source'
        when cpc_group ilike 'G03F7/702%' or cpc_group ilike 'G03F7/703%'
                                                              then 'Exposure: projection & immersion'
        when cpc_group ilike 'G03F7/704%' or cpc_group ilike 'G03F7/705%'
                                                              then 'Exposure: method & dose control'
        when cpc_group ilike 'G03F7/706%'                     then 'Exposure: alignment & overlay'
        when cpc_group ilike 'G03F7/707%' or cpc_group ilike 'G03F7/708%'
             or cpc_group ilike 'G03F7/709%' or cpc_group = 'G03F7/70'
                                                              then 'Exposure: stage, handling & apparatus'

        -- exposure/development step + resist coating (unchanged buckets)
        when cpc_group ilike 'G03F7/2%'                       then 'Illumination / exposure'
        when cpc_group ilike 'G03F7/16%'                      then 'Resist coating'

        -- photoresist compositions & processing (rest of G03F7) — split
        when cpc_group ilike 'G03F7/00%'                      then 'Photoresist compositions'
        when cpc_group ilike 'G03F7/01%' or cpc_group ilike 'G03F7/02%'
             or cpc_group ilike 'G03F7/03%' or cpc_group ilike 'G03F7/06%'
                                                              then 'Resist chemistry & formulation'
        when cpc_group ilike 'G03F7/07%' or cpc_group ilike 'G03F7/09%'
             or cpc_group ilike 'G03F7/10%' or cpc_group ilike 'G03F7/11%'
             or cpc_group ilike 'G03F7/12%' or cpc_group ilike 'G03F7/14%'
                                                              then 'Resist layers & multilayers'
        when cpc_group ilike 'G03F7/30%' or cpc_group ilike 'G03F7/32%'
             or cpc_group ilike 'G03F7/34%' or cpc_group ilike 'G03F7/36%'
             or cpc_group ilike 'G03F7/38%' or cpc_group ilike 'G03F7/40%'
             or cpc_group ilike 'G03F7/42%' or cpc_group ilike 'G03F7/08%'
             or cpc_group ilike 'G03F7/18%'                   then 'Development & resist removal'
        when cpc_group ilike 'G03F7/%'                        then 'Photoresist / other'

        -- alignment / registration
        when cpc_group ilike 'G03F9/%'                        then 'Alignment / registration'
        else 'Other G03F'
    end                                 as subtech
from src
where cpc_subclass = 'G03F'
