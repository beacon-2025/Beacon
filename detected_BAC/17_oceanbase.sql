-- Login with the root user
CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) );
REVOKE ALL ON tbl1 FROM regular_user;
CREATE INDEX my_index ON tbl1 (my_1_col);

-- Login with user 'regular_user'
SELECT * FROM information_schema.statistics;
/*
+---------------+--------------+------------+------------+--------------+------------+--------------+-------------+
| TABLE_CATALOG | TABLE_SCHEMA | TABLE_NAME | NON_UNIQUE | INDEX_SCHEMA | INDEX_NAME | SEQ_IN_INDEX | COLUMN_NAME |
+---------------+--------------+------------+------------+--------------+------------+--------------+-------------+
| def           | test         | tbl1       |          1 | test         | my_index   |            1 | my_1_col    |
+---------------+--------------+------------+------------+--------------+------------+--------------+-------------+
*/