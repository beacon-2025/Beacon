# Detecting Broken Access Control Vulnerabilities in DBMSs via System Catalog Consistency Validation

**Beacon** aims to detect Broken Access Control (BAC) vulnerabilities by validating the consistency between SQL operations and system catalogs.

The key insight of Beacon is that the visibility of objects in the system catalog is consistent with the user's access control: if an object is invisible to a user in the system catalog, the user should not have any access privileges on that.

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
./beacon --dbms clickhouse  # Test ClickHouse
```

Note that this binary needs to be run on x64 architecture Ubuntu 22.04 or higher, or with GLIBC version >= 2.35. If these conditions are not met, consider using Docker to run Ubuntu 22.04 and then execute Beacon within the container:

```bash
docker run --rm --net=host -v ./:/root -it ubuntu:22.04 /root/beacon --dbms mysql
```

The tool will continuously test the target DBMS and output the testing status. If an ERROR level log occurs in the result, it means that Beacon detects a potential BAC vulnerability.

## Bug List

Below is the full list of 30 confirmed BAC vulnerabilities found by **Beacon**.

| ID | DBMS       | Command     | Description                                                                 | Rule           | Status     |
|----|------------|-------------|-----------------------------------------------------------------------------|----------------|------------|
| 1  | MySQL      | SHOW        | `SHOW OPEN TABLES` results leak unauthorized objects                        | result         | Confirmed  |
| 2  | MySQL      | SELECT      | Results of `innodb_fields` leak unauthorized objects                        | result         | Confirmed  |
| 3  | MySQL      | SELECT      | Results of `innodb_datafiles` leak unauthorized objects                     | result         | Confirmed  |
| 4  | MySQL      | SELECT      | Results of `innodb_tablespaces_brief` leak unauthorized objects             | result         | Confirmed  |
| 5  | MySQL      | SELECT      | Results of `tablespaces_extensions` leak unauthorized objects               | result         | Confirmed  |
| 6  | MariaDB    | DROP        | Error messages of `DROP TRIGGER` leak unauthorized objects                  | errmsg         | Confirmed  |
| 7  | MariaDB    | SELECT      | `session_status` lacks proper permission checks                             | result         | Confirmed  |
| 8  | MariaDB    | SELECT      | `global_status` lacks proper permission checks                              | result         | Confirmed  |
| 9  | MariaDB    | SELECT      | `session_account_connect_attrs` lacks proper permission checks              | result         | Confirmed  |
| 10 | OceanBase  | CREATE      | `CREATE TRIGGER` body lacks permission checks                               | cmd            | Confirmed  |
| 11 | OceanBase  | CREATE      | `CREATE FUNCTION` body lacks permission checks                              | cmd            | Confirmed  |
| 12 | OceanBase  | CREATE      | `CREATE PROCEDURE` body lacks permission checks                             | cmd            | Confirmed  |
| 13 | OceanBase  | SHOW        | `SHOW DATABASES STATUS` leaks unauthorized objects                          | result         | Confirmed  |
| 14 | OceanBase  | SHOW        | `SHOW TABLE STATUS` leaks unauthorized objects                              | result         | Confirmed  |
| 15 | OceanBase  | SHOW        | `SHOW FUNCTION STATUS` leaks unauthorized objects                           | result         | Confirmed  |
| 16 | OceanBase  | SELECT      | Results of `parameters` leak unauthorized objects                           | result         | Confirmed  |
| 17 | OceanBase  | SELECT      | Results of `statistics` leak unauthorized objects                           | result         | Confirmed  |
| 18 | OceanBase  | SELECT      | Results of `partitions` leak unauthorized objects                           | result         | Confirmed  |
| 19 | OceanBase  | SELECT      | Results of `view_table_usage` leak unauthorized objects                     | result         | Confirmed  |
| 20 | StarRocks  | SHOW        | `SHOW TABLE STATUS` leaks unauthorized objects                              | result         | Confirmed  |
| 21 | StarRocks  | SHOW        | `SHOW CREATE VIEW` leaks unauthorized objects                               | result         | Confirmed  |
| 22 | StarRocks  | INSERT      | Error messages from `INSERT` leak unauthorized objects                      | errmsg         | Confirmed  |
| 23 | TiDB       | SELECT      | `SELECT ... FOR UPDATE` skips permission checks                             | cmd            | Confirmed  |
| 24 | TiDB       | REPLACE     | `REPLACE VIEW` skips permission checks                                      | cmd            | Confirmed  |
| 25 | TiDB       | DELETE      | `DELETE ... WHERE` skips permission checks                                  | cmd            | Confirmed  |
| 26 | Dameng     | SELECT      | `all_tables_dis_info` leaks unauthorized objects                            | result         | Confirmed  |
| 27 | Dameng     | SELECT      | `vsyscolumns` leaks unauthorized objects                                    | result         | Confirmed  |
| 28 | Dameng     | SELECT      | `vsystexts` leaks unauthorized objects                                      | result         | Confirmed  |
| 29 | Dameng     | CREATE      | Ownership confusion in certain `CREATE SCHEMA` usage                        | cmd            | Confirmed  |
| 30 | ClickHouse | EXPLAIN     | `EXPLAIN QUERY` leaks unauthorized objects                                  | result         | Confirmed  |
