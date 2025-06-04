{{
    config(
        materialized='incremental',
        unique_key=['base_currency', 'quote_currency', 'timestamp_utc']
    )
}}

select
    base_currency,
    quote_currency,
    timestamp as timestamp_utc,  -- Standardize timestamp to UTC
    case
        when exchange_rate <= 0 then null
        else exchange_rate
    end as exchange_rate
from {{ ref('exchange_rates') }}
where
    base_currency is not null
    and quote_currency is not null
    and exchange_rate is not null
    {% if is_incremental() %}
        and timestamp > (
            select max(timestamp_utc)
            from {{ this }}
        )
    {% endif %}
qualify row_number() over (
    partition by base_currency, quote_currency, timestamp
    order by exchange_rate desc
) = 1
