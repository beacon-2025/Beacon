
-- login as the root user
CREATE TABLE x (x INT PRIMARY KEY);
REVOKE DELETE ON x FROM regular_user;

-- Login as the user 'regular_user'
DELETE FROM x WHERE x = 2147483647;
-- ERROR 1142 (42000): SELECT command denied to user 'regular_user'@'%' for table 'x'
DELETE FROM x WHERE x = 2147483648;
-- Query OK, 0 rows affected (0.01 sec)