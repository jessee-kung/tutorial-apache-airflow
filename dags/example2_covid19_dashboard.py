from datetime import datetime, timedelta
import logging

import pendulum

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from airflow.models import Variable

from airflow.models.param import Param

logger = logging.getLogger("airflow.task")

pqload_job_input_path = "/opt/data/source"
pqload_job_output_path = "/opt/data/daily"

dbload_job_input_path = "/opt/data/daily"
dbload_job_output_db_host = Variable.get("mariadb_host")
dbload_job_output_db_port = Variable.get("mariadb_port")
dbload_job_output_db_name = Variable.get("mariadb_name")
dbload_job_output_db_user = Variable.get("mariadb_user")
dbload_job_output_db_passwd = Variable.get("mariadb_passwd")

with DAG(
    dag_id="example2_covid19_dashboard",
    schedule_interval="0 0 * * *",
    start_date=pendulum.datetime(2020, 1, 1, tz="UTC"),
    catchup=False,
    dagrun_timeout=timedelta(minutes=60),
    params={
        "start_date": Param(
            default="{}".format(
                (datetime.today() - timedelta(days=3)).date().strftime("%Y-%m-%d")
            ),
            type="string",
        ),
    },
) as dag:
    # Download source payload
    download_job = BashOperator(
        task_id="download_job",
        bash_command="/opt/airflow/dags/bing_covid19/download.sh ",
    )

    # Daily job
    daily_job = SparkSubmitOperator(
        task_id="daily_job",
        application="/opt/airflow/dags/bing_covid19/etl.py",
        application_args=[
            "--worker",
            "daily",
            "--start-date",
            "{{params.start_date}}",
            "--input-path",
            pqload_job_input_path,
            "--output-path",
            pqload_job_output_path,
        ],
    )

    # Regional-based Job
    regional_based_job = SparkSubmitOperator(
        task_id="regional_based_job",
        application="/opt/airflow/dags/bing_covid19/etl.py",
        application_args=[
            "--worker",
            "regional_based",
            "--start-date",
            "{{params.start_date}}",
            "--input-path",
            dbload_job_input_path,
            "--output-db-host",
            dbload_job_output_db_host,
            "--output-db-port",
            dbload_job_output_db_port,
            "--output-db-name",
            dbload_job_output_db_name,
            "--output-db-user",
            dbload_job_output_db_user,
            "--output-db-passwd",
            dbload_job_output_db_passwd,
        ],
    )

    # Countery-based Job
    country_based_job = SparkSubmitOperator(
        task_id="country_based_job",
        application="/opt/airflow/dags/bing_covid19/etl.py",
        application_args=[
            "--worker",
            "country_based",
            "--start-date",
            "{{params.start_date}}",
            "--input-path",
            dbload_job_input_path,
            "--output-db-host",
            dbload_job_output_db_host,
            "--output-db-port",
            dbload_job_output_db_port,
            "--output-db-name",
            dbload_job_output_db_name,
            "--output-db-user",
            dbload_job_output_db_user,
            "--output-db-passwd",
            dbload_job_output_db_passwd,
        ],
    )
    download_job >> daily_job

    daily_job >> regional_based_job
    daily_job >> country_based_job

if __name__ == "__main__":
    dag.cli()
