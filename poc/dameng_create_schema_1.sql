-- Login as the root user
SET SCHEMA REGULAR_USER;
CREATE SCHEMA test;

-- Login as user 'regular_user'
DROP SCHEMA test;
/* Query OK */