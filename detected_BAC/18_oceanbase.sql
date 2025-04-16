-- Login with the root user
CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) );
REVOKE ALL ON tbl1 FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM information_schema.partitions;
/*
+------------------+-------------------------------+
| TABLE_SCHEMA     | TABLE_NAME                    |
+------------------+-------------------------------+
| test             | tbl1                          |
+------------------+-------------------------------+
*/
