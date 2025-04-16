-- Login with the root user
CREATE USER foo;
GRANT CREATE ROUTINE ON *.* TO regular_user;

-- Login with user 'regular_user'
DELIMITER $$
CREATE PROCEDURE unwant_grant() BEGIN GRANT ALL ON *.* TO foo; END $$
CALL unwant_grant() $$
DELIMITER ;
/* Query OK */