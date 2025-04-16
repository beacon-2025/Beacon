-- Login with the root user
CREATE TABLE tbl1 (col1 TEXT);
GRANT CREATE ROUTINE ON *.* TO regular_user;
CREATE TABLE tbl2 (col2 TEXT);
GRANT SELECT ON tbl2 TO regular_user;
INSERT INTO tbl1 VALUES ('some text');

-- Login with user 'regular_user'
DELIMITER $$
CREATE FUNCTION my_function (func_args_1 INT) RETURNS INT DETERMINISTIC BEGIN INSERT INTO tbl2 SELECT * FROM tbl1; RETURN 1; END $$
SELECT my_function(1) $$
DELIMITER ;
/* Query OK */