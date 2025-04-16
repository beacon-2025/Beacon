-- Login with the root user
CREATE TABLE tbl1 (x int);
CREATE INDEX idx1 on tbl1(x);
REVOKE SELECT ON tbl1 FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM information_schema.INNODB_FIELDS;
/*
+--------------------+--------------------+-----+
| INDEX_ID           | NAME               | POS |
+--------------------+--------------------+-----+
| 0x33               | database_name      |   0 |
| 0x33               | table_name         |   1 |
...
| 0x3333353538       | x                  |   0 |
+--------------------+--------------------+-----+