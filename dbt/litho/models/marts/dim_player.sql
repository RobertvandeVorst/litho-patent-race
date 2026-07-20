select
    player,
    any_value(player_country)   as player_country,
    any_value(player_category)  as player_category,
    count(*)                    as total_patents,
    min(grant_year)             as first_year,
    max(grant_year)             as last_year
from {{ ref('fct_patent') }}
group by player
