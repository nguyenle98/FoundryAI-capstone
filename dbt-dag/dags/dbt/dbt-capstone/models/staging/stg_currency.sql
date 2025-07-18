with source as (
    select
     DISTINCT currency, code
    from {{ source('api_sources', 'currency') }}
    
)

select * from source