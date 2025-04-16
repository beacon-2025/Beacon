"""
该文件存储一系列路径变量，表示各个 JDBC 驱动的 jar 包路径和 class 名称。
"""

import os
from dataclasses import dataclass

JDBC_PACKAGE_PATH = os.path.dirname(os.path.abspath(__file__))


@dataclass
class LibJDBCConfig:
    jar_path: str      # jar 包的绝对路径，例如 "/path/to/dm-jdbc-driver-1.0.jar"
    class_name: str    # driver class 的名称，例如 "dm.jdbc.driver.DmDriver"
    uri_template: str  # uri 的格式，例如 "jdbc:dm://{host}:{port}"，其中 {host} 和 {port} 会被替换为实际的 host 和 port


LIBJDBC_CONFIGS: dict[str, LibJDBCConfig] = {
}


def add_config(dsn: str, jar_path: str, class_name: str, uri_template: str):
    LIBJDBC_CONFIGS[dsn] = LibJDBCConfig(jar_path, class_name, uri_template)


DAMENG_JAR_18 = os.path.join(JDBC_PACKAGE_PATH, "DmJdbcDriver18.jar")
DAMENG_CLASS = "dm.jdbc.driver.DmDriver"
DAMENG_URI = "jdbc:dm://{host}:{port}?schema={database}"
add_config("dameng", DAMENG_JAR_18, DAMENG_CLASS, DAMENG_URI)

GBASE8S_JAR_3_5_1 = os.path.join(JDBC_PACKAGE_PATH, "gbasedbtjdbc_3.5.1.jar")
GBASE8S_CLASS = "com.gbasedbt.jdbc.Driver"
GBASE8S_URI = "jdbc:gbasedbt-sqli://{host}:{port}/testdb:GBASEDBTSERVER=gbase01;DB_LOCALE=zh_CN.utf8;CLIENT_LOCALE=zh_CN.utf8;IFX_LOCK_MODE_WAIT=30;"
add_config("gbase8s", GBASE8S_JAR_3_5_1, GBASE8S_CLASS, GBASE8S_URI)

HIVE_JAR_4_0_0 = os.path.join(JDBC_PACKAGE_PATH, "hive-jdbc-4.0.0-standalone.jar")
HIVE_CLASS = "org.apache.hive.jdbc.HiveDriver"
HIVE_URI = "jdbc:hive2://{host}:{port}/"
add_config("hive", HIVE_JAR_4_0_0, HIVE_CLASS, HIVE_URI)

YASHANDB_JAR_1_6_9 = os.path.join(JDBC_PACKAGE_PATH, "yashandb-jdbc-1.6.9.jar")
YASHANDB_CLASS = "com.yashandb.jdbc.Driver"
YASHANDB_URI = "jdbc:yasdb://{host}:{port}/yashandb"
add_config("yashandb", YASHANDB_JAR_1_6_9, YASHANDB_CLASS, YASHANDB_URI)

POSTGRESQL_JAR_42_7_4 = os.path.join(JDBC_PACKAGE_PATH, "postgresql-42.7.4.jar")
POSTGRESQL_CLASS = "org.postgresql.Driver"
POSTGRESQL_URI = "jdbc:postgresql://{host}:{port}/{database}"
add_config("postgresql", POSTGRESQL_JAR_42_7_4, POSTGRESQL_CLASS, POSTGRESQL_URI)

MYSQL_JAR_9_1_0 = os.path.join(JDBC_PACKAGE_PATH, "mysql-connector-j-9.1.0.jar")
MYSQL_CLASS = "com.mysql.cj.jdbc.Driver"
MYSQL_URI = "jdbc:mysql://{host}:{port}/{database}"
add_config("mysql", MYSQL_JAR_9_1_0, MYSQL_CLASS, MYSQL_URI)
