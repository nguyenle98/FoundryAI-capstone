{{
    config(
        materialized='incremental',
        unique_key=['base_currency', 'quote_currency', 'timestamp_utc']
    )
}}

select
    ce.base_currency,
    ce.quote_currency,
    ce.timestamp as timestamp_utc,
    case
        when ce.exchange_rate <= 0 then null
        else ce.exchange_rate
    end as exchange_rate
from {{ ref('exchange_rates') }} as ce
where
    ce.base_currency is not null
    and ce.quote_currency is not null
    and ce.exchange_rate is not null
    {% if is_incremental() %}
        and ce.timestamp > (
            select max(ce2.timestamp_utc)
            from {{ this }} as ce2
        )
    {% endif %}
qualify row_number() over (
    partition by ce.base_currency, ce.quote_currency, ce.timestamp
    order by ce.exchange_rate desc
) = 1
