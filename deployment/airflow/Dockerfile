FROM apache/airflow:2.3.4

USER root
RUN mkdir -p /etc/apt/keyrings && \
    curl https://packages.adoptium.net/artifactory/api/gpg/key/public | tee /etc/apt/keyrings/adoptium.asc && \
    echo "deb [signed-by=/etc/apt/keyrings/adoptium.asc] https://packages.adoptium.net/artifactory/deb $(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release) main" | tee /etc/apt/sources.list.d/adoptium.list && \
    apt update && \
    apt install -y temurin-8-jdk
RUN echo export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac)))) >> /root/.bashrc

USER airflow
RUN pip install --no-cache-dir apache-airflow-providers-apache-spark && \
    echo export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac)))) >> /home/airflow/.bashrc && \
    echo export SPARK_HOME=/home/airflow/.local/lib/python3.7/site-packages/pyspark >> /home/airflow/.bashrc
RUN pip install mysql-connector-python==8.0.29