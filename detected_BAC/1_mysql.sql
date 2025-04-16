-- Login with the root user
CREATE TABLE tbl1 (a TEXT);
REVOKE SELECT ON tbl1 FROM regular_user;

-- Login with user 'regular_user'
SHOW OPEN TABLES;
-- Empty set (0.00 sec)

SHOW COLLATION;
SHOW DATABASES; 
SHOW FUNCTION STATUS;
SHOW OPEN TABLES;
/*
+--------------------+---------------------------+--------+-------------+
| Database           | Table                     | In_use | Name_locked |
+--------------------+---------------------------+--------+-------------+
| information_schema | CHARACTER_SETS            |      0 |           0 |
| information_schema | COLLATIONS                |      0 |           0 |
...
| mysql              | tbl1                      |      0 |           0 |
...
+--------------------+---------------------------+--------+-------------+