SELECT role_name AS name, 'ROLE' AS type, null AS parentname FROM information_schema.enabled_roles;
SELECT table_name AS name, 'TABLE' AS type, table_schema AS parentname FROM information_schema.tables WHERE table_type = 'BASE TABLE';
SELECT table_name AS name, 'VIEW' AS type, table_schema AS parentname FROM information_schema.views;
SELECT column_name AS name, 'COLUMN' AS type, table_name AS parentname FROM information_schema.columns;
SELECT routine_name AS name, 'FUNCTION' AS type, routine_schema AS parentname FROM information_schema.routines WHERE routine_type = 'FUNCTION';
SELECT routine_name AS name, 'PROCEDURE' AS type, routine_schema AS parentname FROM information_schema.routines WHERE routine_type = 'PROCEDURE';
SELECT constraint_name AS name, 'INDEX_CONSTRAINT' AS type, table_schema AS parentname FROM information_schema.table_constraints WHERE constraint_type IN ('PRIMARY KEY', 'UNIQUE');
SELECT sequence_name AS name, 'SEQUENCE' AS type, sequence_schema AS parentname FROM information_schema.sequences;
SELECT schema_name AS name, 'SCHEMA' AS type, null AS parentname FROM information_schema.schemata WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema';