-- Login with the root user
CREATE TABLE tbl (x INT);
CREATE TRIGGER before_insert_tbl
BEFORE INSERT ON tbl FOR EACH ROW INSERT INTO test SELECT 1;
REVOKE TRIGGER ON before_insert_tbl FROM regular_user;

-- Login with user 'regular_user'
DROP TRIGGER before_insert_tbl;
-- ERROR 1142 (42000): TRIGGER command denied to user 'regular_user'@'localhost' for table `test`.`tbl`