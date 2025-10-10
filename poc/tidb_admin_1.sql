-- Login as user 'root'
INSERT INTO mysql.expr_pushdown_blacklist VALUES('<','tikv','');
GRANT SELECT ON test.* TO regular_user;

-- Login as user 'regular_user'
ADMIN RELOAD EXPR_PUSHDOWN_BLACKLIST;
-- Query OK, 0 rows affected (0.001 sec)