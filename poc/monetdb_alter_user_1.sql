-- Log in as the root user 'monetdb' and create a regular user
CREATE USER test WITH PASSWORD 'test' NAME 'test';

-- Log in as the user 'test' with password 'test'

-- Try altering the root user directly, which will fail
ALTER USER monetdb MAX_WORKERS 10
-- [OUTPUT] Insufficient privileges to change user 'monetdb'

-- Execute the SET SESSION statement and retry, which will succeed (should fail)
SET SESSION AUTHORIZATION monetdb;
ALTER USER monetdb MAX_WORKERS 10;
-- [OUTPUT] operation successful