-- Login as the root user
GRANT USAGE ON test.* TO regular_user;

-- Login as user 'regular_user'
CALL DBMS_STATS.CREATE_STAT_TABLE('mysql', 'stats_table3');
/* Query OK */

-- Login as user 'root'
SELECT * FROM mysql.stats_table3;
-- The query will ok, which means the stats_table3 is created successfully by 'regular_user'.