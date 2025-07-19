{{ config(
    materialized='incremental',
    unique_key=['quote_currency', 'timestamp'],
    incremental_strategy='merge'
) }}

/*
This is dimensional modeling. 
*/

with source as (
    select
        base_currency,
        quote_currency,
        exchange_rate,
        timestamp,
        ingested_at,
    from {{ ref('stg_exchange_rates') }}
    {% if is_incremental() %}
    where timestamp > (select max(timestamp) from {{ this }})
    {% endif %}
), currency as (
    select
        currency,
        code
    from {{ ref('stg_currency') }}
), final as (
    select
        s.base_currency,
        s.quote_currency,
        s.exchange_rate,
        s.timestamp,
        s.ingested_at,
        c.code as quote_currency_code,
        c.currency
    from source s
    left join currency c on s.quote_currency = c.code
    
)
select * from final



