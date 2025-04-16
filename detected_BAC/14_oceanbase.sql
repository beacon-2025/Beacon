-- Login with the root user
CREATE TABLE tbl1 (col1 INT, col2 INT, col3 INT);
GRANT SELECT ON tbl1 TO regular_user;
CREATE VIEW view1 AS SELECT * FROM tbl1;
REVOKE ALL ON view1 FROM regular_user;

-- Login with user 'regular_user'
SHOW TABLE STATUS;
/*
+-------+-----------+---------+------------+------+-----+
| Name  | Engine    | Version | Row_format | Rows | ... |
+-------+-----------+---------+------------+------+-----+
| tbl1  | oceanbase |       0 | DYNAMIC    |    0 | ... |
| view1 | NULL      |    NULL | NULL       | NULL | ... |
+-------+-----------+---------+------------+------+-----+
*/