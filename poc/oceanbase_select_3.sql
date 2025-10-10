-- Login as the root user
CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) );
CREATE INDEX my_index ON tbl1 (my_1_col);

-- Login as user 'regular_user'
SELECT * FROM STATISTICS;
/*
+---------------+--------------+------------+------------+--------------+------------+--------------+-------------+
| TABLE_CATALOG | TABLE_SCHEMA | TABLE_NAME | NON_UNIQUE | INDEX_SCHEMA | INDEX_NAME | SEQ_IN_INDEX | COLUMN_NAME |
+---------------+--------------+------------+------------+--------------+------------+--------------+-------------+
| def           | test         | tbl1       |          1 | test         | my_index   |            1 | my_1_col    |
+---------------+--------------+------------+------------+--------------+------------+--------------+-------------+