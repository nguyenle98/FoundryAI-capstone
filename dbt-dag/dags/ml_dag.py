from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import subprocess

def run_ml_inference():
    subprocess.run(["python", "/usr/local/airflow/dags/ml_volatility_classifier.py"], check=True)

with DAG(
    dag_id="ml_inference_dag",
    start_date=datetime(2024, 7, 19),
    schedule=None,
    catchup=False,
) as dag:
    ml_task = PythonOperator(
        task_id="run_ml_model",
        python_callable=run_ml_inference,
    )