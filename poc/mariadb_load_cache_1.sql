-- Login as the root user
CREATE TABLE table1 (col1 INT, col2 INT, INDEX index1 (col1));

-- Login as user 'regular_user'
LOAD INDEX INTO CACHE table1 KEY (index1);
/*
+-------------+--------------+----------+-----------------------------------+
| Table       | Op           | Msg_type | Msg_text                          |
+-------------+--------------+----------+-----------------------------------+
| test.table1 | preload_keys | Error    | Table 'test.table1' doesn't exist |
| test.table1 | preload_keys | status   | Operation failed                  |
+-------------+--------------+----------+-----------------------------------+
2 rows in set (0.000 sec)