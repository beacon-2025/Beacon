-- Login with the root user
CREATE TABLE tbl1 (col1 INT, col2 INT, col3 INT);
REVOKE INSERT ON tbl1 TO regular_user;

-- Login with user 'regular_user'
INSERT INTO test.tbl1 VALUES ( DEFAULT );
-- ERROR 5604 (22000): Getting analyzing error. Detail message: Inserted target column count: 3 doesn't match select/value column count: 1.

INSERT INTO test.tbl1 VALUES ( DEFAULT, DEFAULT, DEFAULT );
-- ERROR 1064 (HY000): Getting analyzing error. Detail message: Column has no default value, column=col1.

INSERT INTO test.tbl1 VALUES ( NULL, DEFAULT, DEFAULT );
-- ERROR 1064 (HY000): Getting analyzing error. Detail message: Column has no default value, column=col2.

INSERT INTO test.tbl1 VALUES ( NULL, NULL, DEFAULT );
-- ERROR 1064 (HY000): Getting analyzing error. Detail message: Column has no default value, column=col3.