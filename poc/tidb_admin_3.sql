-- Login as the root user
SHOW PLUGINS;
GRANT SELECT ON test.* TO regular_user;

-- Login as user 'regular_user'
ADMIN PLUGINS ENABLE some_plugin;
-- Query OK, 0 rows affected (0.001 sec)
