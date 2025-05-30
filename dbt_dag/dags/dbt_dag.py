import os
from datetime import datetime
from cosmos import DbtDag, ProjectConfig, ProfileConfig, ExecutionConfig
from cosmos.profiles import SnowflakeUserPasswordProfileMapping

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