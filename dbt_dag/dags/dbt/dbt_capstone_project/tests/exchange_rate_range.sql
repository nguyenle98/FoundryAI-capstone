select *
from {{ ref('exchange_metrics') }}
where exchange_rate > 1000000  -- Unreasonably high rate
   or exchange_rate < 0.00001  -- Unreasonably low rate