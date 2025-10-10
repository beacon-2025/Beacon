-- Login as the root user
GRANT USAGE ON SCHEMA public TO regular_user;
CREATE TYPE private_type AS (lft INT, rht INT);
REVOKE USAGE ON TYPE private_type FROM PUBLIC;
-- Verify that regular_user has NO privilege
SELECT has_type_privilege('regular_user', 'private_type', 'USAGE');
-- Result: f
GRANT CREATE ON SCHEMA public TO regular_user;

-- Login as user 'regular_user'
CREATE TYPE my_range AS RANGE (subtype = private_type);
-- Result: CREATE TYPE returns successfully (UNEXPECTED)
SELECT n.nspname AS schema,
       t.typname AS type_name,
       pg_get_userbyid(t.typowner) AS owner
FROM pg_type t
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE t.typowner = 'regular_user'::regrole;
/*
 schema |   type_name    | owner
--------+----------------+-------
 public | my_range       | regular_user
 public | my_multirange  | regular_user
 public | _my_range      | regular_user
 public | _my_multirange | regular_user
(4 rows)
*/
CREATE DOMAIN my_domain AS private_type;
-- ERROR:  permission denied for type private_type