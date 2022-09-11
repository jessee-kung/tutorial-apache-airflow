import argparse
import collections
import os
import glob
import shutil

from typing import List
from datetime import datetime, timedelta
from pyspark.sql import SparkSession, DataFrame, functions as F
import mysql.connector


class ParquetEnumerator:
    def __init__(self, payload_root: str, partitions: List[str]):
        self._payload_root = payload_root
        self._partitions = partitions

    def list_all(self, path_validation: bool = True) -> List[str]:
        ParquetPath = collections.namedtuple("ParquetPath", self._partitions + ["path"])

        fmt = self._payload_root
        for partition in self._partitions:
            fmt = os.path.join(fmt, "{}=*".format(partition))
        fmt = os.path.join(fmt, "*.parquet")

        sols = []
        for path_ in glob.glob(fmt):
            if path_validation:
                for partition, subpath in zip(
                    self._partitions,
                    path_.replace(self.payload_root, "").split(os.sep)[1:-1],
                ):
                    tokens = subpath.split("=")
                    assert tokens[0] == partition
            sols.append(path_)
        return sols

    @property
    def payload_root(self) -> str:
        return self._payload_root


class BingCovid19ETL:
    def __init__(
        self,
        worker: str,
        start_date: datetime,
        input_path: str,
        output_path: str = None,
        output_db_host: str = None,
        output_db_name: str = None,
        output_db_user: str = None,
        output_db_passwd: str = None,
        output_db_port: int = 3306,
        app_name: str = "covid19-dashboard-etl",
    ):
        self._worker = worker
        self._start_date = start_date

        # For all ETL
        self._input_path = input_path

        # For daily
        if worker == "daily" and output_path is None:
            raise ValueError(
                "invalid argument: 'output_path', must be provided for worker: '{}'".format(
                    worker
                )
            )
        self._output_path = output_path

        # For regional_based and country_based
        if worker == "regional_based" or worker == "country_based":
            for k, v in [
                ("output_db_host", output_db_host),
                ("output_db_name", output_db_name),
                ("output_db_user", output_db_user),
                ("output_db_passwd", output_db_passwd),
                ("output_db_port", output_db_port),
            ]:
                if v is None:
                    raise ValueError(
                        "invalid argument: '{}', must be provided for worker: '{}'".format(
                            k, worker
                        )
                    )
        self._output_jdbc_url = "jdbc:mariadb://{}:{}/{}?user={}&password={}".format(
            output_db_host,
            output_db_port,
            output_db_name,
            output_db_user,
            output_db_passwd,
        )
        self._output_db_host = output_db_host
        self._output_db_port = output_db_port
        self._output_db_name = output_db_name
        self._output_db_user = output_db_user
        self._output_db_passwd = output_db_passwd

        self._spark = (
            SparkSession.builder.master("spark://spark:7077")
            .appName(app_name)
            .enableHiveSupport()
            .getOrCreate()
        )
        print("spark session created")

    def __del__(self):
        self._spark.stop()
        print("spark session destroyed")

    def _purge_parquet(self):
        now = datetime.now()
        curr = self._start_date
        while curr.date() <= now.date():
            path_ = os.path.join(
                self._output_path,
                "updated={}".format(curr.strftime("%Y-%m-%d")),
            )
            if os.path.exists(path_):
                shutil.rmtree(
                    path_,
                )
            curr = curr + timedelta(days=1)

    def _purge_db_table(self, table_name: str):
        conn = mysql.connector.connect(
            host=self._output_db_host,
            database=self._output_db_name,
            port=self._output_db_port,
            user=self._output_db_user,
            password=self._output_db_passwd,
        )
        updated_ = self._start_date.strftime("%Y-%m-%d")

        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM {} WHERE updated >= '{}'".format(table_name, updated_)
        )
        cursor.close()
        conn.close()

    def _daily(self):
        self._purge_parquet()

        ds = self._read()
        ds = (
            ds.filter(F.col("country_region") != "Worldwide")
            .filter((F.col("confirmed_change") >= 0) & (F.col("deaths_change") >= 0))
            .fillna(0)
            .sort(
                F.col("updated"),
                F.col("country_region"),
                F.col("admin_region_1"),
                F.col("admin_region_2"),
            )
            .write.option("maxRecordsPerFile", 262144)
            .option("header", True)
            .partitionBy("updated")
            .mode("append")
            .parquet(self._output_path)
        )

    def _regional_based(self):
        self._purge_db_table("regional_based")
        ds = self._read(["updated"])
        ds = (
            ds.groupBy(
                F.col("updated"),
                F.col("country_region"),
                F.col("admin_region_1"),
                F.col("admin_region_2"),
                F.col("latitude"),
                F.col("longitude"),
            )
            .agg(
                F.sum(F.col("deaths_change")).alias("death"),
                F.sum(F.col("confirmed_change")).alias("confirmed"),
            )
            .withColumn(
                "region",
                F.when(
                    (
                        F.col("admin_region_1").isNotNull()
                        & F.col("admin_region_2").isNotNull()
                    ),
                    F.concat(
                        F.col("country_region"),
                        F.lit(", "),
                        F.col("admin_region_1"),
                        F.lit(", "),
                        F.col("admin_region_2"),
                    ),
                )
                .when(
                    (F.col("admin_region_1").isNotNull()),
                    F.concat(
                        F.col("country_region"), F.lit(", "), F.col("admin_region_1")
                    ),
                )
                .when(
                    (F.col("admin_region_2").isNotNull()),
                    F.concat(
                        F.col("country_region"), F.lit(", "), F.col("admin_region_2")
                    ),
                )
                .otherwise(F.col("country_region")),
            )
            .select(
                F.col("updated"),
                F.col("region"),
                F.col("latitude"),
                F.col("longitude"),
                F.col("death"),
                F.col("confirmed"),
            )
            .sort("updated")
            .write.format("jdbc")
            .mode("append")
            .option("driver", "org.mariadb.jdbc.Driver")
            .option("url", self._output_jdbc_url)
            .option("truncate", "true")
            .option("dbtable", "regional_based")
            .save()
        )

    def _country_based(self):
        self._purge_db_table("country_based")
        ds = self._read(["updated"])
        ds = (
            ds.groupBy(F.col("updated"), F.col("country_region"))
            .agg(
                F.sum(F.col("deaths_change")).alias("death"),
                F.sum(F.col("confirmed_change")).alias("confirmed"),
            )
            .withColumnRenamed("country_region", "country")
            .select(
                F.col("updated"), F.col("country"), F.col("death"), F.col("confirmed")
            )
            .sort("updated")
            .write.format("jdbc")
            .mode("append")
            .option("driver", "org.mariadb.jdbc.Driver")
            .option("url", self._output_jdbc_url)
            .option("truncate", "true")
            .option("dbtable", "country_based")
            .save()
        )

    def _read(self, partitions: List[str] = []) -> DataFrame:
        print("input path: {}".format(self._input_path))
        path_parquets = ParquetEnumerator(self._input_path, partitions).list_all()
        print("enumerate path of parquets: {}".format(path_parquets))

        return (
            self._spark.read.option("basePath", self._input_path)
            .parquet(*path_parquets)
            .filter(F.col("updated") >= self._start_date)
        )

    def run(self):
        if self._worker == "daily":
            self._daily()
        elif self._worker == "country_based":
            self._country_based()
        elif self._worker == "regional_based":
            self._regional_based()
        else:
            raise LookupError("unknown worker: '{}'".format(self._worker))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", help="worker type", type=str)
    parser.add_argument("--start-date", help="start date", type=str)
    parser.add_argument("--input-path", help="input path", type=str)
    parser.add_argument("--output-path", help="output path", type=str, default=None)
    parser.add_argument("--output-db-host", help="output path", type=str, default=None)
    parser.add_argument("--output-db-port", help="output path", type=int, default=3306)
    parser.add_argument("--output-db-name", help="output path", type=str, default=None)
    parser.add_argument("--output-db-user", help="output path", type=str, default=None)
    parser.add_argument(
        "--output-db-passwd", help="output path", type=str, default=None
    )
    args = parser.parse_args()

    start_date_ = datetime.strptime(args.start_date, "%Y-%m-%d")
    etl_worker = BingCovid19ETL(
        worker=args.worker,
        start_date=start_date_,
        input_path=args.input_path,
        output_path=args.output_path,
        output_db_host=args.output_db_host,
        output_db_port=args.output_db_port,
        output_db_name=args.output_db_name,
        output_db_user=args.output_db_user,
        output_db_passwd=args.output_db_passwd,
    )
    etl_worker.run()
