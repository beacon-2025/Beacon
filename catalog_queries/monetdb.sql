SELECT name, 'SCHEMA' AS type, NULL AS parentname FROM sys.schemas;
SELECT t.name, 'TABLE' AS type, s.name AS parentname FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.id;
SELECT table_type_id FROM sys.table_types WHERE table_type_name = 'VIEW';
SELECT c.name, 'COLUMN' AS type, tbl.name AS parentname FROM sys.columns c JOIN sys.tables tbl ON c.table_id = tbl.id;
SELECT name, 'USER' AS type, NULL AS parentname FROM sys.users;
SELECT name, 'ROLE' AS type, NULL AS parentname FROM sys.roles;
SELECT u.name || ' -> ' || r.name AS name, 'USER_ROLE' AS type, NULL AS parentname FROM sys.user_role ur JOIN sys.auths u ON ur.login_id = u.id JOIN sys.roles r ON ur.role_id = r.id;