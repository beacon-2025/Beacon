-- Login with the root user
CREATE TABLE tbl1 (col1 INT, col2 INT, col3 INT);
GRANT SELECT ON tbl1 TO regular_user;
CREATE VIEW view1 AS SELECT * FROM tbl1;
REVOKE ALL ON view1 FROM regular_user;

-- Login with user 'regular_user'
SHOW TABLE STATUS;
/*
+-------+--------+---------+------------+------+----------------+-------------+-----------------+--------------+-----------+----------------+---------------------+---------------------+------------+-----------------+----------+----------------+---------+
| Name  | Engine | Version | Row_format | Rows | Avg_row_length | Data_length | Max_data_length | Index_length | Data_free | Auto_increment | Create_time         | Update_time         | Check_time | Collation       | Checksum | Create_options | Comment |
+-------+--------+---------+------------+------+----------------+-------------+-----------------+--------------+-----------+----------------+---------------------+---------------------+------------+-----------------+----------+----------------+---------+
| view1 | NULL   |    NULL |            |   -1 |             -1 |          -1 |            NULL |         NULL |      NULL |           NULL | 2024-12-08 16:58:15 | 1969-12-31 23:59:59 | NULL       | utf8_general_ci |     NULL |                |         |
+-------+--------+---------+------------+------+----------------+-------------+-----------------+--------------+-----------+----------------+---------------------+---------------------+------------+-----------------+----------+----------------+---------+
*/
