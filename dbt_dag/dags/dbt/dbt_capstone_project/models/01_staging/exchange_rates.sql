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
from {{ source('exchange_rates_bronze', 'RAW_KAFKA_EVENTS_FLAT') }}