-- Login with the root user
DELIMITER $$ 
CREATE FUNCTION my_function (func_args_1 INT) RETURNS INT DETERMINISTIC BEGIN RETURN 1; END $$
DELIMITER ;
REVOKE ALL ON my_function FROM regular_user;

-- Login with user 'regular_user'
SHOW FUNCTION STATUS;
/*
+------+-------------+----------+------------+-----+
| Db   | Name        | Type     | Definer    | ... |
+------+-------------+----------+------------+-----+
| db   | my_function | FUNCTION | 'root'@'%' | ... |
+------+-------------+----------+------------+-----+
*/