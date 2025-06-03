FROM apache/airflow:2.10.5
RUN pip install apache-airflow-providers-snowflake
RUN cp dbt_pt /usr/dbt