{{
  config(
    materialized='view'
  )
}}

select
  base_currency,
  quote_currency,
  exchange_rate,
  timestamp
from {{ source('sc_lab_m1w4', 'forex_crypto_rates_wayne') }}
