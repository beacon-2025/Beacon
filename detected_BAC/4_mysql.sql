-- Login with the root user
CREATE TABLE tbl1 (x int);
REVOKE SELECT ON tbl1 FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM information_schema.INNODB_TABLESPACES_BRIEF;
/*
+------------------------+-----------------+------------------------+--------------+------------+
| SPACE                  | NAME            | PATH                   | FLAG         | SPACE_TYPE |
+------------------------+-----------------+------------------------+--------------+------------+
| 0x30                   | innodb_system   | ibdata1                | 0x3138343332 | System     |
| 0x34323934393637323739 | innodb_undo_001 | ./undo_001             | 0x30         | Single     |
...
| 0x3239303238           | test/tbl1       | ./test/tbl1.ibd        | 0x3136343137 | Single     |
+------------------------+-----------------+------------------------+--------------+------------+