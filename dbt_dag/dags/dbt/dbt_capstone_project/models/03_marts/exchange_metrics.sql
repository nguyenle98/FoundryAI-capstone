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
        timestamp_utc,  -- Use the non-keyword column name
        lag(exchange_rate) over (
            partition by base_currency, quote_currency
            order by timestamp_utc
        ) as prev_rate
    from {{ ref('clean_exchange_rates') }}
    {% if is_incremental() %}
        where timestamp_utc > (
            select coalesce(max(timestamp_utc), '1900-01-01')
            from {{ this }}
        )
    {% endif %}
)

select
    base_currency,
    quote_currency,
    exchange_rate,
    prev_rate,
    timestamp_utc,
    case
        when prev_rate is null then null
        else (exchange_rate - prev_rate) / prev_rate * 100
    end as pct_change
from ranked
