'''This is a OneBigTable because:

All data is in one denormalized table
No joins needed to get complete information
Each row contains all necessary information (base currency, quote currency, rate, timestamp)'''

{{ config(
    materialized='incremental',
    unique_key=['quote_currency', 'timestamp'],
    incremental_strategy='merge'
) }}

with source as (
    select
        base_currency,
        quote_currency,
        exchange_rate,
        timestamp,
        ingested_at,
        -- Take the latest record by ingested_at for each currency pair and timestamp
        row_number() over (
            partition by quote_currency, timestamp 
            order by ingested_at desc
        ) as rn
    from {{ ref('stg_exchange_rates') }}
),

deduplicated as (
    select
        base_currency,
        quote_currency,
        exchange_rate,
        timestamp
    from source
    where rn = 1  -- Keep only the latest record
)

select * from deduplicated

{% if is_incremental() %}
    where timestamp > (select max(timestamp) from {{ this }})
{% endif %}