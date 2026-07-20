with src as (select * from {{ source('raw', 'assignee') }})

select
    patent_id::varchar                              as patent_id,
    try_cast(assignee_sequence as int)              as assignee_sequence,
    assignee_id                                     as assignee_id,
    trim(disambig_assignee_organization)            as org
from src
where disambig_assignee_organization is not null
  and trim(disambig_assignee_organization) <> ''
