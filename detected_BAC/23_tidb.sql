-- Login with the root user
CREATE TABLE tbl1 (x int);
GRANT SELECT ON tbl1 TO regular_user;
INSERT INTO tbl1 VALUES (100);

-- Login with user 'regular_user'
SELECT * FROM tbl1 FOR UPDATE;
/* Query OK */