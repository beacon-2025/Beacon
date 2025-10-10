-- Log in as the root user 'monetdb' and create a regular user
CREATE USER test WITH PASSWORD 'test' NAME 'test';

-- Log in as the user 'test' with password 'test';
SET SCHEMA sys;
CREATE TABLE x (y INT);
-- CREATE TABLE: insufficient privileges for user 'test' in schema 'sys'

-- Log in as the user 'test' with password 'test';
ALTER USER test DEFAULT ROLE monetdb;
-- operation successful
-- It means that the MonetDB does not check the permission of the ALTER USER ... DEFAULT ROLE statement.

-- Log in as the user 'test' with password 'test';
SET SCHEMA sys;
CREATE TABLE x (y INT);
-- operation successful