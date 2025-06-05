{{
    config(
        materialized='incremental',
        unique_key=['base_currency', 'quote_currency', 'timestamp']
    )
}}

with max_existing as (
    select
        {% if is_incremental() %}
            max(timestamp) as max_timestamp
        {% else %}
            cast('1900-01-01' as timestamp) as max_timestamp
        {% endif %}
    from {{ this }}
),

ranked as (
    select
        base_currency,
        quote_currency,
        exchange_rate,
        timestamp_utc,
        lag(exchange_rate) over (
            partition by base_currency, quote_currency
            order by timestamp_utc
        ) as prev_rate
    from {{ ref('clean_exchange_rates') }}
    where timestamp_utc > (select max_timestamp from max_existing)
)

select
    base_currency,
    quote_currency,
    exchange_rate,
    prev_rate,
    timestamp_utc as timestamp,
    case
        when prev_rate is null then null
        else (exchange_rate - prev_rate) / prev_rate * 100
    end as pct_change
from ranked
