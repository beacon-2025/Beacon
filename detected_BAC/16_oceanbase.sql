-- Login with the root user
DELIMITER $$
CREATE FUNCTION my_function (func_args_1 INT) RETURNS INT DETERMINISTIC BEGIN RETURN 1; END $$
DELIMITER ;
REVOKE ALL ON my_function FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM information_schema.parameters;
/*
+------------------+-----------------+---------------+------------------+----------------+----------------+
| SPECIFIC_CATALOG | SPECIFIC_SCHEMA | SPECIFIC_NAME | ORDINAL_POSITION | PARAMETER_MODE | PARAMETER_NAME |
+------------------+-----------------+---------------+------------------+----------------+----------------+
| def              | test            | my_function   |                0 | NULL           | NULL           |
| def              | test            | my_function   |                1 | IN             | func_args_1    |
+------------------+-----------------+---------------+------------------+----------------+----------------+
*/
