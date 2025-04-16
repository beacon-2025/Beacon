-- Login with the root user
CREATE TABLE tbl1 (a INT);
GRANT DELETE ON tbl1 TO foo;

-- Login with user 'regular_user'
DELETE FROM tbl1 WHERE 2>1;
/* ERROR 1142 (42000): SELECT command denied to user 'foo'@'%' for table 'tbl1' */
