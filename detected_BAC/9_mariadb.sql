-- Login with the root user
REVOKE SELECT ON performance_schema.session_account_connect_attrs FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM performance_schema.session_account_connect_attrs;
/* Query OK */