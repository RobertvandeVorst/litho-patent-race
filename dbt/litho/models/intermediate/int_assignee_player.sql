-- Collapses the many raw org-name variants into canonical "players", then tags
-- each player with a country and an industry category. Anything unmatched falls
-- through to 'Other', so the pipeline never silently drops rows.
--
-- Matching is deliberately tolerant (ilike, punctuation- and case-insensitive) but
-- guarded against look-alikes: e.g. 'micron technology' (not Micronic/Unimicron),
-- 'sumitomo chemical' (not Sumitomo Electric/Heavy), 'rohm and haas' (not Rohm Co).

with a as (select * from {{ ref('stg_assignee') }}),

tagged as (
    select
        patent_id,
        assignee_sequence,
        org,
        case
            -- equipment / optics / light sources
            when org ilike '%asml%'                                          then 'ASML'
            when org ilike '%canon%'                                         then 'Canon'
            when org ilike '%nikon%'                                         then 'Nikon'
            when org ilike '%zeiss%'                                         then 'Carl Zeiss'
            when org ilike '%tokyo electron%'                                then 'Tokyo Electron'
            when org ilike '%applied materials%'                            then 'Applied Materials'
            when org ilike '%gigaphoton%'                                    then 'Gigaphoton'
            when org ilike '%cymer%'                                         then 'Cymer'
            when org ilike '%molecular imprint%'                            then 'Molecular Imprints'
            -- chipmakers / device & panel makers
            when org ilike '%taiwan semiconductor%' or org ilike '%tsmc%'    then 'TSMC'
            when org ilike '%samsung%'                                       then 'Samsung'
            when org ilike '%intel%'                                         then 'Intel'
            when org ilike '%international business machines%' or org ilike '%ibm%' then 'IBM'
            when org ilike '%toshiba%'                                       then 'Toshiba'
            when org ilike '%micron technology%'                            then 'Micron'
            when org ilike '%hynix%'                                         then 'SK Hynix'
            when org ilike '%globalfoundries%' or org ilike '%global foundries%' then 'GlobalFoundries'
            when org ilike '%boe %' or org ilike '%boe,%'                    then 'BOE'
            when org ilike '%winbond%'                                       then 'Winbond'
            when org ilike '%infineon%'                                      then 'Infineon'
            when org ilike '%fujitsu%'                                       then 'Fujitsu'
            -- materials / photoresist / chemicals
            when org ilike '%shin-etsu%'                                     then 'Shin-Etsu'
            when org ilike '%fujifilm%' or org ilike '%fuji film%'           then 'FUJIFILM'
            when org ilike '%ohka%'                                          then 'Tokyo Ohka'
            when org ilike 'jsr%'                                            then 'JSR'
            when org ilike '%rohm and haas%'                                 then 'Rohm & Haas'
            when org ilike '%sumitomo chemical%'                            then 'Sumitomo Chemical'
            when org ilike '%nissan chemical%'                             then 'Nissan Chemical'
            -- metrology / EDA
            when org ilike 'kla %' or org ilike 'kla-%'                      then 'KLA-Tencor'
            when org ilike '%synopsys%'                                      then 'Synopsys'
            -- mask blanks / substrates
            when org ilike '%hoya%'                                          then 'Hoya'
            else 'Other'
        end as player
    from a
)

select
    patent_id,
    assignee_sequence,
    org,
    player,
    case player
        when 'ASML'              then 'NL'
        when 'Canon'             then 'JP'
        when 'Nikon'             then 'JP'
        when 'Carl Zeiss'        then 'DE'
        when 'Tokyo Electron'    then 'JP'
        when 'Applied Materials' then 'US'
        when 'Gigaphoton'        then 'JP'
        when 'Cymer'             then 'US'
        when 'Molecular Imprints' then 'US'
        when 'TSMC'              then 'TW'
        when 'Samsung'           then 'KR'
        when 'Intel'             then 'US'
        when 'IBM'               then 'US'
        when 'Toshiba'           then 'JP'
        when 'Micron'            then 'US'
        when 'SK Hynix'          then 'KR'
        when 'GlobalFoundries'   then 'US'
        when 'BOE'               then 'CN'
        when 'Winbond'           then 'TW'
        when 'Infineon'          then 'DE'
        when 'Fujitsu'           then 'JP'
        when 'Shin-Etsu'         then 'JP'
        when 'FUJIFILM'          then 'JP'
        when 'Tokyo Ohka'        then 'JP'
        when 'JSR'               then 'JP'
        when 'Rohm & Haas'       then 'US'
        when 'Sumitomo Chemical' then 'JP'
        when 'Nissan Chemical'   then 'JP'
        when 'KLA-Tencor'        then 'US'
        when 'Synopsys'          then 'US'
        when 'Hoya'              then 'JP'
        else null
    end as player_country,
    case player
        when 'ASML'              then 'Equipment'
        when 'Canon'             then 'Equipment'
        when 'Nikon'             then 'Equipment'
        when 'Carl Zeiss'        then 'Equipment'
        when 'Tokyo Electron'    then 'Equipment'
        when 'Applied Materials' then 'Equipment'
        when 'Gigaphoton'        then 'Equipment'
        when 'Cymer'             then 'Equipment'
        when 'Molecular Imprints' then 'Equipment'
        when 'TSMC'              then 'Chipmaker'
        when 'Samsung'           then 'Chipmaker'
        when 'Intel'             then 'Chipmaker'
        when 'IBM'               then 'Chipmaker'
        when 'Toshiba'           then 'Chipmaker'
        when 'Micron'            then 'Chipmaker'
        when 'SK Hynix'          then 'Chipmaker'
        when 'GlobalFoundries'   then 'Chipmaker'
        when 'BOE'               then 'Chipmaker'
        when 'Winbond'           then 'Chipmaker'
        when 'Infineon'          then 'Chipmaker'
        when 'Fujitsu'           then 'Chipmaker'
        when 'Shin-Etsu'         then 'Materials'
        when 'FUJIFILM'          then 'Materials'
        when 'Tokyo Ohka'        then 'Materials'
        when 'JSR'               then 'Materials'
        when 'Rohm & Haas'       then 'Materials'
        when 'Sumitomo Chemical' then 'Materials'
        when 'Nissan Chemical'   then 'Materials'
        when 'KLA-Tencor'        then 'Metrology-EDA'
        when 'Synopsys'          then 'Metrology-EDA'
        when 'Hoya'              then 'Mask-substrate'
        else 'Other'
    end as player_category
from tagged
