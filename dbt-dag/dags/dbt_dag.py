import os
from datetime import datetime
from cosmos import DbtDag, ProjectConfig, ProfileConfig, ExecutionConfig
from cosmos.profiles import SnowflakeUserPasswordProfileMapping

PROJECT_DIR = '/usr/local/airflow/dags/dbt/dbt-capstone'

profile_config = ProfileConfig(
    profile_name="capstone",
    target_name="dev",
    profile_mapping=SnowflakeUserPasswordProfileMapping(
        conn_id="snowflake_conn",
        profile_args={
            "database": "CAPSTONE_FINAL",
            "schema": "DB_SCHEMA",
            "warehouse": "WH_NGUYEN"
        },
    )
)

dbt_snowflake_dag = DbtDag(
    project_config=ProjectConfig(PROJECT_DIR),
    operator_args={
        "install_deps": True,
        "select": ["stg_exchange_rates", "mart_exchange_rates"]
    },
    profile_config=profile_config,
    execution_config=ExecutionConfig(
        dbt_executable_path=f"{os.environ['AIRFLOW_HOME']}/dbt_venv/bin/dbt"
    ),
    schedule="@daily",
    start_date=datetime(2023, 9, 10),
    catchup=False,
    dag_id="dbt_dag",
)

dag = dbt_snowflake_dag 