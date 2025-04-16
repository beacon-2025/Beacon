-- Login with the root user
CREATE DATABASE test;
REVOKE ALL ON test.* FROM regular_user;

-- Login with user 'regular_user'
SHOW DATABASE STATUS;
/*
+--------------------+------------+
| Database           | Status     |
+--------------------+------------+
| oceanbase          | read write |
| information_schema | read write |
| mysql              | read write |
| SYS                | read write |
| LBACSYS            | read write |
| ORAAUDITOR         | read write |
| test               | read write |
| sys_external_tbs   | read write |
| ocs                | read write |
| db                 | read write |
+--------------------+------------+
*/