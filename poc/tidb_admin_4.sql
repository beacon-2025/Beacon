-- Login as the root user
SHOW PLUGINS;
ADMIN PLUGINS ENABLE some_plugin;
GRANT SELECT ON test.* TO regular_user;

-- Login as user 'regular_user'
ADMIN PLUGINS DISABLE some_plugin;
-- Query OK, 0 rows affected (0.001 sec)
