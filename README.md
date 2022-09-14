# tutorial-apache-airflow
Apache airflow tutorial for beginners. The tutorial sample code is delivered as a Docker Compose, which modified from the [official Apache Airflow Docker Compose](https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html), but adding additional features below:
- Grafana
- MariaDB
    - Dependency of Grafana
- Apache Spark Clusters
    - By default: 1 master + 4 worker nodes
## Getting Started
Please have the Docker community installed first
1. Clone the repository
2. Navigate to the repository root folder
3. Run:
    ```
    $ docker compose up -d
    ```
## Entrypoints
Most of services with Web UI interfaces have set the port forwarding as below:
| Components | URL | Credential|
| ---- | ---- | ---- |
| Airflow | http://localhost:8080 | airflow / airflow |
| Grafana | http://localhost:4040 | admin / admin |
| Spark | http://localhost:8088 | |
| Spark (Application UI) | http://localhost:4040 |

## Development
The `dags` folder are directly mounted as Airflow DAGs root folder. You can develop your DAGs under it.

Dependencies:
- Python 3.7+
- PySpark
- Airflow
- Airflow Apache Spark Provider
- MySQL Connector 8.0.29 / Python

Once can install the dependencies as below:
```
$ pip install -r requirements.txt
```