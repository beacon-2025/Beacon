## System Catalog Queries

This directory contains the system catalog queries used by Beacon to validate access control consistency in different DBMSs.
Each SQL file corresponds to a specific DBMS and includes queries to retrieve information about users, tables, views, columns, and other relevant objects from the system catalogs.

```bash
├── dameng.sql
├── mariadb.sql
├── monetdb.sql
├── mysql.sql
├── oceanbase.sql
├── starrocks.sql
└── tidb.sql
```

For example, `mysql.sql` contains 10 queries:

```sql
-- 1. current user
SELECT SUBSTRING_INDEX(USER(), '@', 1) AS name, 'USER' AS type, null AS parentname;
-- 2. other user and roles
SELECT DISTINCT user AS name, 'USER' AS type, null AS parentname FROM mysql.user;
-- 3. tables
SELECT table_name AS name, 'TABLE' AS type, '' AS parentname FROM information_schema.tables WHERE table_type='BASE TABLE';
-- 4. columns
SELECT column_name AS name, 'COLUMN' AS type, table_name AS parentname FROM information_schema.columns;
-- 5. views
SELECT table_name AS name, 'VIEW' AS type, null AS parentname FROM information_schema.VIEWS;
-- 6. events
SELECT event_name AS name, 'EVENT' AS type, null AS parentname FROM information_schema.events;
-- 7. routines
SELECT DISTINCT routine_name AS name, routine_type AS type, null AS parentname FROM information_schema.ROUTINES;
-- 8. triggers
SELECT trigger_name AS name, 'TRIGGER' AS type, null AS parentname FROM information_schema.triggers;
-- 9. indexes
SELECT table_name AS name, 'STATISTICS' AS type, null AS parentname FROM information_schema.statistics;
-- 10. schemas / databases
SELECT SCHEMA_NAME AS name, 'SCHEMA' AS type, null AS parentname FROM information_schema.SCHEMATA;
```