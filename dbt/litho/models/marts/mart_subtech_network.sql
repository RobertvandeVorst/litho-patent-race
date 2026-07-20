-- Edge list for the hero network: player  --(weight = #patents)-->  sub-technology.
-- Nodes are derived in the frontend from the distinct players + subtechs here.

select
    player,
    subtech,
    count(*) as weight
from {{ ref('fct_patent') }}
where player <> 'Other'
group by player, subtech
having count(*) > 0
order by player, weight desc
