-- Login as the root user
CREATE TABLE tbl1 (a INT);
GRANT DELETE ON tbl1 TO regular_user;

-- Login as user 'regular_user'
DELETE FROM tbl1 WHERE 2>1;
-- ERROR 1142 (42000): SELECT command denied to user 'regular_user'@'%' for table 'tbl1'
-- Expected: Query OK