select
    player,
    any_value(player_country)                               as player_country,
    count(*)                                                as total_patents,
    row_number() over (order by count(*) desc)              as rank
from {{ ref('fct_patent') }}
where player <> 'Other'
group by player
order by total_patents desc
