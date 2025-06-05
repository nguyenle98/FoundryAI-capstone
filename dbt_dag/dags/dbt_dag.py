import os
from datetime import datetime
from cosmos import DbtDag, ProjectConfig, ProfileConfig, ExecutionConfig
from cosmos.profiles import SnowflakeUserPasswordProfileMapping
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

# Set project directory for Astronomer
PROJECT_DIR = '/usr/local/airflow/dags/dbt/dbt_capstone_project'

profile_config = ProfileConfig(
    profile_name="capstone_project",  # Match your dbt_project.yml profile name
    target_name="dev",
    profile_mapping=SnowflakeUserPasswordProfileMapping(
        conn_id="snowflake_academy",  
        profile_args={
            "database": "CAPSTONE", 
            "schema": "SC_LAB_M1W4",
            "warehouse": "WH_DBT_NGUYENLE"
        },
    )
)

dbt_snowflake_dag = DbtDag(
    project_config=ProjectConfig(PROJECT_DIR),
    operator_args={
        "install_deps": True,
        "retries": 2
    },
    profile_config=profile_config,
    execution_config=ExecutionConfig(
        dbt_executable_path=f"{os.environ['AIRFLOW_HOME']}/dbt_venv/bin/dbt",
    ),
    schedule="@daily",  
    start_date=datetime(2023, 9, 10),
    catchup=False,
    dag_id="dbt_dag",
)
# Trigger the ML DAG after dbt finishes
trigger_ml_dag = TriggerDagRunOperator(
    task_id="trigger_ml_model_dag",
    trigger_dag_id="ml_model_dag",  # This must match your ML DAG's dag_id
    wait_for_completion=False,
    reset_dag_run=True,
    dag=dbt_snowflake_dag,
)

# I tried to use callback on success and dataset expecting dbt_dag and ml_dag to run sequentially, but it didn't work as expected. 