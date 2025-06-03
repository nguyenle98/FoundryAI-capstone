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
      order by timestamp
    ) as prev_rate,
    timestamp
  from {{ ref('exchange_rates') }}
  {% if is_incremental() %}
    where timestamp > (select max(timestamp) from {{ this }})
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