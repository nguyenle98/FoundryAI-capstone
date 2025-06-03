import logging
import requests

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.operators.bash import BashOperator


# ── Constants ──────────────────────────────────────────────────────────────────
DAG_ID     = "real_time_forex_crypto_pipeline"
TABLE_NAME = "forex_crypto_rates_wayne" 
API_URL    = "https://api.exchangerate.host/live?access_key=24350d1a3226aad12b9e47f7fe2fc424"

# ── Helper ─────────────────────────────────────────────────────────────────────
def get_snowflake_hook():
    return SnowflakeHook(snowflake_conn_id="snowflake_academy")

# ── Tasks ──────────────────────────────────────────────────────────────────────
@task()
def extract_data():
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    # print(f"API response: {payload}")  --> Debugging line, can be removed later

    # live endpoint uses "source" instead of "base"
    base = payload.get("base") or payload.get("source")
    if not base:
        logging.error(f"Unexpected payload keys: {list(payload.keys())}")
        raise KeyError("Missing 'base' or 'source' in API response")

    ts = payload.get("timestamp") or int(datetime.now(timezone.utc).timestamp())
    quotes = payload.get("quotes") or payload.get("rates") or {}

    records = []
    for pair, rate in quotes.items():
        # e.g. "USDGBP" → base="USD", quote="GBP"
        quote = pair[len(base):] if pair.startswith(base) else pair
        records.append((base, quote, rate, datetime.fromtimestamp(ts, tz=timezone.utc)))

    logging.info(f"Extracted {len(records)} records for base={base}")
    return records

@task()
def chunk_data(records: list[tuple], chunk_size: int = 50) -> list[list[tuple]]:
    return [records[i:i + chunk_size] for i in range(0, len(records), chunk_size)]

@task()
def insert_data(records: list[tuple]):
    from math import ceil

    CHUNK_SIZE = 50           # Tune this: 50–200 is usually safe
    MAX_THREADS = 4           # Tune based on CPU/Snowflake load

    # Chunk the records
    chunks = [records[i:i + CHUNK_SIZE] for i in range(0, len(records), CHUNK_SIZE)]

    # Define the worker function
    def insert_chunk(chunk):
        hook = get_snowflake_hook()
        hook.insert_rows(table=TABLE_NAME, rows=chunk, commit_every=CHUNK_SIZE)

    # Use ThreadPoolExecutor to parallelize inserts
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        executor.map(insert_chunk, chunks)

    return f"Inserted {len(records)} records in {len(chunks)} chunks using {MAX_THREADS} threads"

@task()
def transform_data():
    hook = get_snowflake_hook()
    
    hook.run(f"""
        CREATE OR REPLACE TABLE CAPSTONE.SC_LAB_M1W4.currency_dedup AS (
            SELECT DISTINCT * FROM CAPSTONE.SC_LAB_M1W4.forex_crypto_rates_wayne
        )
    """)
    hook.run(f"""
        INSERT INTO CAPSTONE.SC_LAB_M1W4.processed_exchange_rates_wayne
        WITH ranked AS (
            SELECT
                r.base_currency,
                r.quote_currency,
                r.exchange_rate,
                LAG(r.exchange_rate) OVER (
                    PARTITION BY r.base_currency, r.quote_currency
                    ORDER BY r.timestamp
                ) AS prev_rate,
                r.timestamp
            FROM CAPSTONE.SC_LAB_M1W4.currency_dedup r
            WHERE r.timestamp > (SELECT MAX(timestamp) FROM CAPSTONE.SC_LAB_M1W4.processed_exchange_rates_wayne)
        )
        SELECT
            ranked.base_currency,
            ranked.quote_currency,
            ranked.exchange_rate,
            ranked.prev_rate,
            CASE
              WHEN ranked.prev_rate IS NULL THEN NULL
              ELSE (ranked.exchange_rate - ranked.prev_rate) / ranked.prev_rate * 100
            END AS pct_change,
            ranked.timestamp
        FROM ranked     
    """)
    hook.run(f"""
         CREATE OR REPLACE TABLE CAPSTONE.SC_LAB_M1W4.EXPENSES_WAYNE AS (
         SELECT *, spending_amount * exchange_rate AS SPENDING_IN_USD FROM CAPSTONE.SC_LAB_M1W4.mock_spending
            LEFT JOIN CAPSTONE.SC_LAB_M1W4.processed_exchange_rates_wayne ON   
            mock_spending.currency_code = processed_exchange_rates_wayne.quote_currency AND
            mock_spending.ts = processed_exchange_rates_wayne.timestamp);
    """)
    return "transform complete"

@task()
def validate_transformed_data():
    hook = get_snowflake_hook()

    # 1. Check if table exists
    table_check = hook.get_first("""
        SELECT COUNT(*) 
        FROM CAPSTONE.INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = 'PROCESSED_EXCHANGE_RATES_WAYNE'
          AND TABLE_SCHEMA = 'SC_LAB_M1W4'
    """)
    if table_check[0] == 0:
        raise ValueError("Table processed_exchange_rates_wayne does not exist.")

    # 2. Check if the table has at least 1 row
    row_check = hook.get_first("""
        SELECT COUNT(*) FROM CAPSTONE.SC_LAB_M1W4.PROCESSED_EXCHANGE_RATES_WAYNE
    """)
    if row_check[0] == 0:
        raise ValueError("Table exists but has no rows.")

    # 3. Check for NULLs in critical columns
    null_check = hook.get_first("""
        SELECT COUNT(*) FROM CAPSTONE.SC_LAB_M1W4.PROCESSED_EXCHANGE_RATES_WAYNE
        WHERE base_currency IS NULL OR quote_currency IS NULL 
        OR exchange_rate IS NULL OR timestamp IS NULL
    """)
    if null_check[0] > 0:
        raise ValueError("Found NULLs in critical columns.")

    # 4. Check if at least some pct_change values are not null
    pct_check = hook.get_first("""
        SELECT COUNT(*) FROM CAPSTONE.SC_LAB_M1W4.PROCESSED_EXCHANGE_RATES_WAYNE
        WHERE pct_change IS NOT NULL
    """)
    if pct_check[0] == 0:
        raise ValueError("All pct_change values are NULL.")

    return "validation complete"



# ── DAG Definition ─────────────────────────────────────────────────────────────
@dag(
    dag_id=DAG_ID,
    start_date=days_ago(1),
    schedule_interval=timedelta(hours=1),
    catchup=False,
    tags=["forex", "crypto", "elt"],
)
def forex_crypto_pipeline():
    records     = extract_data()
    inserted    = insert_data(records)
    transformed = transform_data()
    validated   = validate_transformed_data()

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/airflow/dbt_capstone_project && dbt run --full-refresh",
    )

    # Set dependencies
    records >> inserted >> transformed >> validated >> dbt_run

    # Optionally return all tasks for Airflow to register them
    return [records, inserted, transformed, validated, dbt_run]

dag = forex_crypto_pipeline()




'''
Data is stored in at least two tables in Snowflake:

forex_crypto_rates_wayne → raw data

processed_exchange_rates_wayne → transformed data

currency_dim_wayne → dimension table (bonus!)
'''

'''
At least one join operation is used in the processing pipeline:

FROM ranked     
        JOIN currency_dim_wayne d
          ON ranked.base_currency = d.currency;

 ranked is a list of transactions that happened.

currency_dim_wayne is your list of official currencies you care about.

The JOIN ensures you're only processing transactions involving known currencies.  
'''

'''
Data transformation:

LAG() window function to get prev_rate

Computed column: (exchange_rate - prev_rate) / prev_rate * 100 AS pct_change

DISTINCT for building the dimension table

Filtering and handling of NULLs in validation

Implicit type conversions (timestamps, floats, strings)
'''
