# Detecting Broken Access Control Vulnerabilities in DBMSs via System Catalog Consistency Validation

**Beacon** aims to detect Broken Access Control (BAC) vulnerabilities by validating the consistency between SQL operations and system catalogs.

The key insight of Beacon is that the visibility of objects in the system catalog is consistent with the user's access control: if an object is invisible to a user in the system catalog, the user should not have any access privileges on that.

This artifact contains the following parts:
```bash
├── beacon           # 1. The executable binary of Beacon
├── detected_BAC/    # 2. Details of detected broken access control vulnerabilities
└── README.md        # 3. Introduction to Beacon and how to run it
```

## How to Run Beacon

First, start the databases with Docker:
```bash
# MySQL
docker run -e MYSQL_ALLOW_EMPTY_PASSWORD=1 -p 3306:3306 -itd --name some-mysql mysql:9.2.0
# MariaDB
docker run -itd --name some-mariadb --env MARIADB_ALLOW_EMPTY_ROOT_PASSWORD=1 -p 3309:3306 mariadb:11.6.1-rc
# OceanBase
docker run -p 2881:2881 --name some-oceanbase -e MODE=slim -d oceanbase/oceanbase-ce:4.3.4.0-100000162024110717
# StarRocks
docker run -p 9030:9030 -p 8030:8030 -p 8040:8040 -itd --name some-starrocks starrocks/allin1-ubuntu:3.3.5
# TiDB
docker run -d --name some-tidb -p 4000:4000 -p 10080:10080 pingcap/tidb:v9.0.0-beta.1
# Dameng
docker run -d -p 30236:5236 --restart=always --name=some-dameng --privileged=true -e LD_LIBRARY_PATH=/opt/dmdbms/bin -e PAGE_SIZE=16 -e EXTENT_SIZE=32 -e LOG_SIZE=1024 -e UNICODE_FLAG=1  -e INSTANCE_NAME=dm8_test greyhawk/dm8_single:dm8_20241022_rev244896_x86_rh6_64
# ClickHouse
docker run -d -p 8123:8123 --name some-clickhouse-server --ulimit nofile=262144:262144 -e CLICKHOUSE_PASSWORD='default' -e CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1 clickhouse/clickhouse-server:25.3.2
```

Second, execute Beacon with the `--dbms` argument. Available argument values include `mysql,mariadb,oceanbase,starrocks,tidb,dameng,clickhouse`:
```bash
./beacon --dbms mysql       # Test MySQL
./beacon --dbms mariadb     # Test MariaDB
./beacon --dbms oceanbase   # Test OceanBase
./beacon --dbms starrocks   # Test StarRocks
./beacon --dbms tidb        # Test TiDB
./beacon --dbms dameng      # Test Dameng
./beacon --dbms clickhouse  # Test ClickHouse
```

Note that this binary needs to be run on x64 architecture Ubuntu 22.04 or higher, or with GLIBC version >= 2.35. If these conditions are not met, consider using Docker to run Ubuntu 22.04 and then execute Beacon within the container:

```bash
docker run --rm --net=host -v ./:/root -it ubuntu:22.04 /root/beacon --dbms mysql
```

The tool will continuously test the target DBMS and output the testing status. If an ERROR level log occurs in the result, it means that Beacon detects a potential BAC vulnerability.

## Vulnerability List

Below is the full list of 30 confirmed BAC vulnerabilities found by **Beacon**.

| ID | DBMS       | Command | Description                                                              | Rule   | Status    |
|----|------------|---------|--------------------------------------------------------------------------|--------|-----------|
| 1  | MySQL      | SHOW    | Results of the `SHOW OPEN TABLES` leak unauthorized objects              | result | Confirmed |
| 2  | MySQL      | SELECT  | Results of table `innodb_fields` leak unauthorized objects               | result | Confirmed |
| 3  | MySQL      | SELECT  | Results of table `innodb_datafiles` leak unauthorized objects            | result | Confirmed |
| 4  | MySQL      | SELECT  | Results of table `innodb_tablespaces_brief` leak unauthorized objects    | result | Confirmed |
| 5  | MySQL      | SELECT  | Results of table `tablespaces_extensions` leak unauthorized objects       | result | Confirmed |
| 6  | MariaDB    | DROP    | Error messages of `DROP TRIGGER` leak unauthorized objects               | errmsg | Confirmed |
| 7  | MariaDB    | SELECT  | Permission checks for table `session_status` are broken                  | result | Confirmed |
| 8  | MariaDB    | SELECT  | Permission checks for table `global_status` are broken                   | result | Confirmed |
| 9  | MariaDB    | SELECT  | Permission checks for table `session_account_connect_attrs` are broken   | result | Confirmed |
| 10 | OceanBase  | CREATE  | Permission checks for the trigger body of `CREATE TRIGGER` are missing   | cmd    | Confirmed |
| 11 | OceanBase  | CREATE  | Permission checks for the routine body of `CREATE FUNCTION` are missing  | cmd    | Confirmed |
| 12 | OceanBase  | CREATE  | Permission checks for the routine body of `CREATE PROCEDURE` are missing | cmd    | Confirmed |
| 13 | OceanBase  | SHOW    | Results of `SHOW DATABASES STATUS` leak unauthorized objects             | result | Confirmed |
| 14 | OceanBase  | SHOW    | Results of `SHOW TABLE STATUS` leak unauthorized objects                 | result | Confirmed |
| 15 | OceanBase  | SHOW    | Results of `SHOW FUNCTION STATUS` leak unauthorized objects              | result | Confirmed |
| 16 | OceanBase  | SELECT  | Results of table `parameters` leak unauthorized objects                  | result | Confirmed |
| 17 | OceanBase  | SELECT  | Results of table `statistics` leak unauthorized objects                  | result | Confirmed |
| 18 | OceanBase  | SELECT  | Results of table `partitions` leak unauthorized objects                  | result | Confirmed |
| 19 | OceanBase  | SELECT  | Results of table `view_table_usage` leak unauthorized objects            | result | Confirmed |
| 20 | StarRocks  | SHOW    | Results of `SHOW TABLE STATUS` leak unauthorized objects                 | result | Confirmed |
| 21 | StarRocks  | SHOW    | Results of `SHOW CREATE VIEW` leak unauthorized objects                  | result | Confirmed |
| 22 | StarRocks  | INSERT  | Error messages of `INSERT` leak unauthorized objects                     | errmsg | Confirmed |
| 23 | TiDB       | SELECT  | Permission checks for `SELECT ... FOR UPDATE` are missing                | cmd    | Confirmed |
| 24 | TiDB       | REPLACE | Permission checks for `REPLACE VIEW` are missing                         | cmd    | Confirmed |
| 25 | TiDB       | DELETE  | Permission checks for `DELETE ... WHERE` are broken                      | cmd    | Confirmed |
| 26 | Dameng     | SELECT  | Results of table `all_tables_dis_info` leak unauthorized objects         | result | Confirmed |
| 27 | Dameng     | SELECT  | Results of table `vsyscolumns` leak unauthorized objects                 | result | Confirmed |
| 28 | Dameng     | SELECT  | Results of table `vsystexts` leak unauthorized objects                   | result | Confirmed |
| 29 | Dameng     | CREATE  | The owner of schemas is mistaken with specific `CREATE SCHEMA` command   | cmd    | Confirmed |
| 30 | ClickHouse | EXPLAIN | Results of `EXPLAIN QUERY` leak unauthorized objects                     | result | Confirmed |

