-- -- Log in as the root user 'monetdb' and create users for testing
CREATE USER test WITH PASSWORD 'test' NAME 'test';
CREATE USER alice WITH PASSWORD 'alice' NAME 'alice' SCHEMA sys;

-- Log in as the user 'test' with password 'test'
DROP ROLE alice;
DROP USER alice;
-- Both can be executed by the user 'test'

-- Log in as the user 'alice' with password 'alice'
-- SQLException:sql.initClient:42000!The user was not found in the database, this session is going to terminate