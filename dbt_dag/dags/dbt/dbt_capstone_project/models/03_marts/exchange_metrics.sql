{{
  config(
    materialized='incremental',
    unique_key=['base_currency', 'quote_currency', 'timestamp']
  )
}}

with ranked as (
    select
        base_currency,
        quote_currency,
        exchange_rate,
        lag(exchange_rate) over (
            partition by base_currency, quote_currency
            order by timestamp_utc
        ) as prev_rate,
        timestamp_utc as timestamp
    from {{ ref('clean_exchange_rates') }}
    {% if is_incremental() %}
    -- Only process new records since last run
    where timestamp_utc > (select coalesce(max(timestamp), '1900-01-01') from {{ this }})
    {% endif %}
)

select
    base_currency,
    quote_currency,
    exchange_rate,
    prev_rate,
    case
        when prev_rate is null then null
        else (exchange_rate - prev_rate) / prev_rate * 100
    end as pct_change,
    timestamp
from ranked