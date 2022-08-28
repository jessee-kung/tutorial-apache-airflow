# Tutorial-apache-airflow: Notice for Airflow
The `docker-compose.yaml` here is provided by Apache Airflow official. In other words, you can switch to any version when needed.

To obtain the latest version of Airflow Docker Compose, see:  
https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html#docker-compose-yaml

> NOTICE: Please comment the `image` attribute in the common section as below:
> ```yaml
> x-airflow-common:
>     # image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.3.4}   # COMMENT THIS LINE EVERYTIME
> ```