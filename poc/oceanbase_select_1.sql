-- Login as the root user
CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) );
REVOKE ALL ON tbl1 FROM regular_user;

-- Login as user 'regular_user'
SELECT * FROM PARTITIONS;
/*
+------------------+-------------------------------+
| TABLE_SCHEMA     | TABLE_NAME                    |
+------------------+-------------------------------+
| test             | tbl1                          |
+------------------+-------------------------------+
*/
