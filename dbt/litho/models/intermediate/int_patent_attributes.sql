-- Reduce the many-to-one relationships to one primary player and one primary
-- sub-technology per patent, choosing the lead assignee / lead G03F classification.

with player as (
    select patent_id, player, player_country, player_category,
           row_number() over (partition by patent_id order by assignee_sequence) as rn
    from {{ ref('int_assignee_player') }}
),
subtech as (
    select patent_id, subtech,
           row_number() over (partition by patent_id order by cpc_sequence) as rn
    from {{ ref('stg_cpc') }}
),
-- Independent, CPC-based EUV signal. These four leaf codes are EUV-specific
-- (validated: 36-51% overlap with the title flag vs ~4-6% for general optics
-- codes): 7/70033 = EUV/soft-X-ray source, 7/70175 = EUV projection optics,
-- 1/22 = masks for <=100nm radiation, 1/24 = reflection (EUV) masks.
cpc_euv as (
    select patent_id,
           bool_or(cpc_group in ('G03F7/70033','G03F7/70175','G03F1/22','G03F1/24')) as is_euv_cpc
    from {{ ref('stg_cpc') }}
    group by patent_id
)
select
    p.patent_id,
    player.player,
    player.player_country,
    player.player_category,
    subtech.subtech,
    coalesce(cpc_euv.is_euv_cpc, false) as is_euv_cpc
from {{ ref('stg_patent') }} p
left join player   on player.patent_id   = p.patent_id and player.rn  = 1
left join subtech  on subtech.patent_id  = p.patent_id and subtech.rn = 1
left join cpc_euv  on cpc_euv.patent_id  = p.patent_id
