with source as (
    select
        BASE as base_currency,
        try_cast(DATE as bigint) as unix_timestamp,
        to_timestamp_ntz(try_cast(DATE as bigint)) as as_of_time,
        try_parse_json(RATES) as rates
    from {{ source('api_sources', 'live_rates') }}
    where BASE is not null
),

flattened as (
    select
        base_currency,
        -- Convert timestamp to UTC
        convert_timezone('UTC', as_of_time) as timestamp,
        -- Remove 'USD' prefix from quote_currency
        replace(key, base_currency, '') as quote_currency,
        value::float as exchange_rate
    from source,
    lateral flatten(input => source.rates)
)

select
    base_currency,
    quote_currency,
    exchange_rate,
    timestamp
from flattened