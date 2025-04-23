from datetime import datetime, timezone
import logging
import requests

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

# ── Constants ──────────────────────────────────────────────────────────────────
DAG_ID     = "real_time_forex_crypto_pipeline"
TABLE_NAME = "forex_crypto_rates_wayne"
API_URL    = "https://api.exchangerate.host/live?access_key=24350d1a3226aad12b9e47f7fe2fc424"

# ── Helper ─────────────────────────────────────────────────────────────────────
def get_snowflake_hook():
    return SnowflakeHook(snowflake_conn_id="snowflake_academy")

# ── Tasks ──────────────────────────────────────────────────────────────────────
@task()
def create_table():
    hook = get_snowflake_hook()
    hook.run(f"""
        CREATE OR REPLACE TABLE {TABLE_NAME} (
          base_currency  STRING,
          quote_currency STRING,
          exchange_rate  FLOAT,
          timestamp      TIMESTAMP
        )
    """)

@task()
def extract_data():
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

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
def insert_data(records: list[tuple]):
    hook = get_snowflake_hook()
    hook.insert_rows(table=TABLE_NAME, rows=records, commit_every=100)

@task()
def transform_data():
    hook = get_snowflake_hook()

    # 1) Build the currency dimension
    hook.run(f"""
        CREATE OR REPLACE TABLE currency_dim_wayne AS
        SELECT DISTINCT
            base_currency AS currency
        FROM {TABLE_NAME};
    """)

    # 2) Build the processed fact table with a JOIN + windowed prev_rate
    hook.run(f"""
        CREATE OR REPLACE TABLE processed_exchange_rates_wayne AS
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
            FROM {TABLE_NAME} r
        )
        SELECT
            ranked.base_currency,
            d.currency         AS dim_currency,
            ranked.quote_currency,
            ranked.exchange_rate,
            ranked.prev_rate,
            CASE
              WHEN ranked.prev_rate IS NULL THEN NULL
              ELSE (ranked.exchange_rate - ranked.prev_rate) / ranked.prev_rate * 100
            END AS pct_change,
            ranked.timestamp
        FROM ranked
        JOIN currency_dim_wayne d
          ON ranked.base_currency = d.currency;
    """)

    return "transform complete"

@task()
def validate_transformed_data():
    hook = get_snowflake_hook()

    # 1. Check if table exists
    table_check = hook.get_first("""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = 'PROCESSED_EXCHANGE_RATES_WAYNE'
    """)
    if table_check[0] == 0:
        raise ValueError("Table processed_exchange_rates_wayne does not exist.")

    # 2. Check if the table has at least 1 row
    row_check = hook.get_first("""
        SELECT COUNT(*) FROM processed_exchange_rates_wayne
    """)
    if row_check[0] == 0:
        raise ValueError("Table exists but has no rows.")

    # 3. Check for NULLs in critical columns
    null_check = hook.get_first("""
        SELECT COUNT(*) FROM processed_exchange_rates_wayne
        WHERE base_currency IS NULL OR quote_currency IS NULL 
        OR exchange_rate IS NULL OR timestamp IS NULL
    """)
    if null_check[0] > 0:
        raise ValueError("Found NULLs in critical columns.")

    # 4. Check if at least some pct_change values are not null
    pct_check = hook.get_first("""
        SELECT COUNT(*) FROM processed_exchange_rates_wayne
        WHERE pct_change IS NOT NULL
    """)
    if pct_check[0] == 0:
        raise ValueError("All pct_change values are NULL.")

    return "validation complete"



# ── DAG Definition ─────────────────────────────────────────────────────────────
@dag(
    dag_id=DAG_ID,
    start_date=days_ago(1),
    schedule_interval="*/5 * * * *",  # every 5 minutes
    catchup=False,
    tags=["forex", "crypto", "etl"],
)
def forex_crypto_pipeline():
    # Define the DAG tasks
    create      = create_table()
    records     = extract_data()
    inserted    = insert_data(records)
    transformed = transform_data()
    validated = validate_transformed_data()

    create >> records >> inserted >> transformed >> validated

# this line actually registers your DAG
dag = forex_crypto_pipeline()
