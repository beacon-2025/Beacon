-- Login as the root user
ALTER SYSTEM SET resource_limit = TRUE;
GRANT SELECT ON *.* TO regular_user;

-- Login as user 'regular_user'
CALL DBMS_RESOURCE_MANAGER.CREATE_CONSUMER_GROUP('group10', 'Ad-hoc queries group');
/* Query OK */
