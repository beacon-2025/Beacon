-- Login with the root user
CREATE TABLE tbl1 (x int);
REVOKE SELECT ON tbl1 FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM information_schema.TABLESPACES_EXTENSIONS;
/*
+------------------+------------------+
| TABLESPACE_NAME  | ENGINE_ATTRIBUTE |
+------------------+------------------+
| mysql            | NULL             |
| innodb_system    | NULL             |
...
| test/tbl1        | NULL             |
+------------------+------------------+