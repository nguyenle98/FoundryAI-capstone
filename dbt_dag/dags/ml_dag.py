from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import subprocess

def run_ml_script():
    subprocess.run(
        ["python", "/usr/local/airflow/dags/dbt/dbt_capstone_project/ml_model.py"],
        check=True
    )

with DAG(
    dag_id="ml_model_dag",
    start_date=datetime(2023, 9, 10),
    schedule=None,  # Only run when triggered manually
    catchup=False,
) as dag:
    ml_task = PythonOperator(
        task_id="run_ml_model",
        python_callable=run_ml_script,
    )