import os
import requests
import json
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.sdk import Variable, dag, task
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator

def fetch_and_load_to_snowflake(**context):
    # Fetch API data
    url = Variable.get("url", default=None)
    response = requests.get(url)
    data = response.json()

    # Use Airflow's Snowflake connection
    hook = SnowflakeHook(snowflake_conn_id="snowflake_conn")
    conn = hook.get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO RAW.live_rates (base, date, rates, full_response)
        SELECT %s, %s, PARSE_JSON(%s), PARSE_JSON(%s)
    """, (
        data.get("source"),  # base currency
        data.get("timestamp"),  # or use datetime.now() for ingestion time
        json.dumps(data.get("quotes") or {}),
        json.dumps(data)
    ))
    cur.close()
    conn.close()

default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}



with DAG(
    dag_id="Ingest_API",
    default_args=default_args,
    start_date=datetime(2023, 9, 10),
    schedule="*/4 * * * *",  # every 4 minutes
    catchup=False,
) as dag:

    ingest_api = PythonOperator(
        task_id="fetch_and_load_to_snowflake",
        python_callable=fetch_and_load_to_snowflake,
    )
    trigger_dependent_dag = TriggerDagRunOperator(
        task_id="trigger_dependent_dag",
        trigger_dag_id="dbt_dag",
        wait_for_completion=True,
        deferrable=True,
    )
    ingest_api>> trigger_dependent_dag