-- Login as the root user
GRANT SELECT ON test.* TO regular_user;

-- Login as user 'regular_user'
ADMIN RELOAD OPT_RULE_BLACKLIST;
-- Query OK, 0 rows affected (0.001 sec)