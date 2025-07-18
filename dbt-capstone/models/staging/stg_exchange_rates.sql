with source as (
    select
        BASE as base_currency,
        try_cast(DATE as bigint) as unix_timestamp,
        to_timestamp_ntz(try_cast(DATE as bigint)) as as_of_time,
        try_parse_json(RATES) as rates,
        INGESTED_AT as ingested_at
    from {{ source('api_sources', 'live_rates') }}
    where BASE is not null
),

flattened as (
    select
        base_currency,
        convert_timezone('UTC', as_of_time) as timestamp,
        replace(key, base_currency, '') as quote_currency,
        value::float as exchange_rate,
        ingested_at
    from source,
    lateral flatten(input => source.rates)
)

select
    base_currency,
    quote_currency,
    exchange_rate,
    timestamp,
    ingested_at
from flattened