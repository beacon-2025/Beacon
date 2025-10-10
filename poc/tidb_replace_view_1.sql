-- Login as the root user
CREATE VIEW vi AS SELECT 1;
GRANT CREATE VIEW ON *.* TO foo;

-- Login as user 'regular_user'
CREATE OR REPLACE VIEW vi AS SELECT 1, 1;
/* Query OK */
