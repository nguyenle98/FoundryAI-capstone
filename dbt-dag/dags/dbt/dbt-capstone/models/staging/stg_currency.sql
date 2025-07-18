with source as (
    select distinct
        currency,
        code
    from {{ source('api_sources', 'currency') }}
)

select * from source
