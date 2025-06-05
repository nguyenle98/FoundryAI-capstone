-- This test checks for unreasonably high or low exchange rates in the exchange_metrics table (Singular test).
SELECT *
FROM {{ ref('exchange_metrics') }}
WHERE (exchange_rate > 1000000 OR exchange_rate < 0.00001)
  AND quote_currency NOT IN ('BTC', 'XAU', 'XAG')