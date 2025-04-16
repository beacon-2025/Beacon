-- Login with the root user
CREATE TABLE tbl1 (x int);
REVOKE SELECT ON tbl1 FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM information_schema.INNODB_DATAFILES;
/*
+------------------------+------------------------+
| SPACE                  | PATH                   |
+------------------------+------------------------+
| 0x30                   | ibdata1                |
| 0x34323934393637323739 | ./undo_001             |
...
| 0x3239303237           | ./test/tbl1.ibd        |
+------------------------+------------------------+