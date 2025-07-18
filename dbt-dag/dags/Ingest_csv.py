import csv
import os
import requests
import json
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from airflow.sdk import Variable, dag, task
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator



def load_csv_to_snowflake(**context):
        # Use Airflow's Snowflake connection
    hook = SnowflakeHook(snowflake_conn_id="snowflake_conn")
    conn = hook.get_conn()
    cur = conn.cursor()
    # Fetch local csv
    with open('/usr/local/airflow/dags/currency.csv', newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',')
        for row in spamreader:
           print(f"Processing row: {row}")  
            # Process each row
           cur.execute("""
        INSERT INTO RAW.CURRENCY (CURRENCY, CODE)
        SELECT %s, %s
    """, (
        row[0],  
        row[1]),  
        
    )
    cur.close()
    conn.close()

default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


@task.bash
def list_files_within_dag():
    return "ls -l /usr/local/airflow/dags"

with DAG(
    dag_id="batch_ingest_csv",
    default_args=default_args,
    start_date=datetime(2023, 9, 10),
    schedule="@daily",  # every day
    catchup=False,
) as dag:

    ingest_api = PythonOperator(
         task_id="load_csv_to_snowflake",
         python_callable=load_csv_to_snowflake,
     )
    #list_files_within_dag()