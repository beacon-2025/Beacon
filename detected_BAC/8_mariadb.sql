-- Login with the root user
REVOKE SELECT ON performance_schema.global_status FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM performance_schema.global_status;
/* Query OK */