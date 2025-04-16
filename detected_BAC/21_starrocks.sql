-- Login with the root user
CREATE TABLE tbl1 (col1 INT, col2 INT, col3 INT);
REVOKE ALL ON tbl1 TO regular_user;
CREATE VIEW view1 AS SELECT * FROM tbl1;
REVOKE ALL ON view1 FROM regular_user;

-- Login with user 'regular_user'
SHOW CREATE VIEW view1;
/*
+-------+---------------------------------------------------------------------------------+----------------------+----------------------+
| View  | Create View                                                                     | character_set_client | collation_connection |
+-------+---------------------------------------------------------------------------------+----------------------+----------------------+
| view1 | CREATE VIEW `view1` (`col1`) AS SELECT `test`.`tbl1`.`col1` FROM `test`.`tbl1`; | utf8                 | utf8_general_ci      |
+-------+---------------------------------------------------------------------------------+----------------------+----------------------+
*/
