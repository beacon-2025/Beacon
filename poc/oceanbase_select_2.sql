-- Login as the root user
CREATE TABLE tbl2 ( my_2_col VARCHAR(255) );
GRANT SELECT ON tbl2 TO regular_user;
CREATE VIEW my_view AS SELECT * FROM tbl2;
REVOKE ALL ON my_view FROM regular_user;

-- Login as user 'regular_user'
SELECT * FROM VIEW_TABLE_USAGE;
/*
+--------------+-------------+-----------+--------------+------------+---------------+
| VIEW_CATALOG | VIEW_SCHEMA | VIEW_NAME | TABLE_SCHEMA | TABLE_NAME | TABLE_CATALOG |
+--------------+-------------+-----------+--------------+------------+---------------+
| def          | test        | my_view   | test         | tbl2       | def           |
+--------------+-------------+-----------+--------------+------------+---------------+
*/