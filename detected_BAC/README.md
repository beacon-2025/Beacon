Below is the full list of 30 confirmed BAC vulnerabilities found by **Beacon**. The detail of each vulnerability can be found in this directory.

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

Before reproducing each vulnerability, you should follow these steps to set up the test environment:
1. Login with the root user.
2. Execute the following commands:
    ```
    DROP DATABASE IF EXISTS test;
    CREATE DATABASE test;
    USE test;
    DROP USER IF EXISTS regular_user;
    CREATE USER regular_user;
    ```