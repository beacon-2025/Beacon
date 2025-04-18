# This file is a collection of regression and coverage tests
# for WL#5855: Print EXPLAIN in JSON format

--source include/force_myisam_default.inc
--source include/have_myisam.inc
--source include/elide_costs.inc

set end_markers_in_json=on;

--echo # new "FORMAT" keyword doesn't conflict with the FORMAT() function name:

SELECT FORMAT(1, 2), FORMAT(1, 2, 3);

--echo # new "FORMAT" keyword is a valid identifier:

SET @FORMAT=10;
SELECT @FORMAT;

CREATE TABLE t1 (format INT);
SELECT format FROM t1;
DROP TABLE t1;

--echo # different ways of format name writing:

EXPLAIN FORMAT=traditional SELECT 1;
EXPLAIN FORMAT='TrAdItIoNaL' SELECT 1;
EXPLAIN FORMAT=JSON SELECT 1;

--error ER_UNKNOWN_EXPLAIN_FORMAT
EXPLAIN FORMAT=foo SELECT 1;

--echo # various EXPLAIN output

CREATE TABLE t1 (i INT);
CREATE TABLE t2 (i INT);
CREATE TABLE t3 (i INT);
CREATE TABLE t4 (i INT);

--echo # no end markers in JSON:

set end_markers_in_json=off;
EXPLAIN FORMAT=JSON SELECT * FROM t1;
set end_markers_in_json=on;

EXPLAIN             INSERT INTO t1 VALUES (10);
EXPLAIN FORMAT=JSON INSERT INTO t1 VALUES (10);

                   EXPLAIN             SELECT * FROM t1;
PREPARE stmt FROM 'EXPLAIN FORMAT=JSON SELECT * FROM t1';
EXECUTE stmt;
EXECUTE stmt;

INSERT INTO t1 VALUES (1), (2), (3), (4), (5), (6), (7);
INSERT INTO t2 VALUES (1), (2);

--echo # Check materialized derived table

set @optimizer_switch_saved= @@optimizer_switch;
set optimizer_switch='derived_merge=off';
EXPLAIN
SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT a1.i FROM (SELECT * FROM t1) a1, t2) a2) a3) a4;
EXPLAIN FORMAT=JSON
SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT a1.i FROM (SELECT * FROM t1) a1, t2) a2) a3) a4;
set optimizer_switch= @optimizer_switch_saved;

--echo # subquery in WHERE
EXPLAIN             SELECT * FROM t1 WHERE i IN (SELECT i FROM t2 WHERE t1.i = 10 ORDER BY RAND());
EXPLAIN FORMAT=JSON SELECT * FROM t1 WHERE i IN (SELECT i FROM t2 WHERE t1.i = 10 ORDER BY RAND());

--echo # two subqueries in WHERE
EXPLAIN             SELECT * FROM t1
  WHERE i IN (SELECT i FROM t2 WHERE t1.i = 10 ORDER BY RAND())
     OR i IN (SELECT i FROM t4 ORDER BY RAND());
EXPLAIN FORMAT=JSON SELECT * FROM t1
  WHERE i IN (SELECT i FROM t2 WHERE t1.i = 10 ORDER BY RAND())
     OR i IN (SELECT i FROM t4 ORDER BY RAND());

--echo # simple UNION

EXPLAIN             SELECT * FROM t1 UNION SELECT * FROM t2 UNION SELECT * FROM t3;
EXPLAIN FORMAT=JSON SELECT * FROM t1 UNION SELECT * FROM t2 UNION SELECT * FROM t3;

--echo # more complex UNION

EXPLAIN             (SELECT t1.i FROM t1 JOIN t2) UNION ALL (SELECT * FROM t3 WHERE i IN (SELECT i FROM t4 ORDER BY RAND()));
EXPLAIN FORMAT=JSON (SELECT t1.i FROM t1 JOIN t2) UNION ALL (SELECT * FROM t3 WHERE i IN (SELECT i FROM t4 ORDER BY RAND()));

--echo # UNION with subquery in outer ORDER BY

EXPLAIN             (SELECT * FROM t1) UNION (SELECT * FROM t2) ORDER BY (SELECT i LIMIT 1);
EXPLAIN FORMAT=JSON (SELECT * FROM t1) UNION (SELECT * FROM t2) ORDER BY (SELECT i LIMIT 1);

--echo # optimizer-time subquery

--let $query=SELECT * FROM t1 ORDER BY (SELECT LENGTH(1) FROM t2 LIMIT 1)
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query

--echo # subquery in the HAVING clause

--let $query=SELECT * FROM t1 HAVING i > ALL (SELECT i FROM t2) OR i < ALL (SELECT i FROM t2);
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query

--echo # subquery in the GROUP BY clause

--source include/turn_off_only_full_group_by.inc
--let $query=SELECT * FROM t1 GROUP BY i > ALL (SELECT i FROM t2) OR i < ALL (SELECT i FROM t2);
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query
--source include/restore_sql_mode_after_turn_off_only_full_group_by.inc

--echo # subquery in the SELECT list

--let $query=SELECT (SELECT i + 1 FROM t1 ORDER BY RAND() LIMIT 1), i FROM t1;
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query

DROP TABLE t1, t2, t3, t4;

--echo # derived table that is optimized out

CREATE TABLE t1 (i INT);
EXPLAIN SELECT 1 FROM (SELECT 1 AS x FROM t1) tt WHERE x;
EXPLAIN FORMAT= JSON SELECT 1 FROM (SELECT 1 AS x FROM t1) tt WHERE x;
DROP TABLE t1;

--echo # complex subqueries

CREATE TABLE t1 (a INT, b INT);
CREATE TABLE t2 (c INT, d INT);
CREATE TABLE t3 (e INT);
CREATE TABLE t4 (f INT, g INT);
INSERT INTO t1 VALUES (1,10), (2,10);
INSERT INTO t2 VALUES (2,10), (2,20);
INSERT INTO t3 VALUES (10), (30);
INSERT INTO t4 VALUES (2,10), (2,10);

--let $query = SELECT * FROM t1 WHERE t1.a IN (SELECT c FROM t2 WHERE (SELECT e FROM t3) < SOME(SELECT e FROM t3 WHERE t1.b));
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query

DROP TABLE t1, t2, t3, t4;

--echo # semi-join materialization (if enabled)

CREATE TABLE t1 (a INT);
INSERT INTO t1 VALUES (1), (1), (1), (1), (1), (1), (1), (1), (1), (1), (1), (1);
CREATE TABLE t2 (a INT) SELECT * FROM t1;
CREATE TABLE t3 (a INT) SELECT * FROM t1;
CREATE TABLE t4 (a INT) SELECT * FROM t1;

EXPLAIN FORMAT=JSON
SELECT * FROM t1
WHERE t1.a IN (SELECT t2.a FROM t2 WHERE t2.a >  0) AND
      t1.a IN (SELECT t3.a FROM t3 WHERE t3.a IN
	       (SELECT t4.a FROM t4 WHERE a > 0));

DROP TABLE t1, t2, t3, t4;

--echo # the same subquery is associated with two different JOIN_TABs

CREATE TABLE t1 (
  i1 INTEGER NOT NULL,
  c1 VARCHAR(1) NOT NULL
) charset latin1 ENGINE=InnoDB;

INSERT INTO t1 VALUES (2,'w');

CREATE TABLE t2 (
  i1 INTEGER NOT NULL,
  c1 VARCHAR(1) NOT NULL,
  c2 VARCHAR(1) NOT NULL,
  KEY (c1, i1)
) charset latin1 ENGINE=InnoDB;

INSERT INTO t2 VALUES (8,'d','d');
INSERT INTO t2 VALUES (4,'v','v');

CREATE TABLE t3 (
  c1 VARCHAR(1) NOT NULL
) charset latin1 ENGINE=InnoDB;

INSERT INTO t3 VALUES ('v');

EXPLAIN FORMAT=json
SELECT i1
FROM t1
WHERE EXISTS (SELECT t2.c1
              FROM (t2 INNER JOIN t3 ON (t3.c1 = t2.c1))
              WHERE t2.c2 != t1.c1 AND t2.c2 = (SELECT MIN(t3.c1)
                                                FROM t3));

DROP TABLE t1, t2, t3;

--echo # multiple materialization groups

CREATE TABLE t1 (c_key INT, KEY c_key (c_key));
INSERT INTO t1 VALUES (1), (2), (3);
CREATE TABLE t2 (c INT, c_key INT);
INSERT INTO t2 VALUES (8,5),(4,5),(8,1);
CREATE TABLE t3 LIKE t1;
INSERT INTO t3 SELECT * FROM t1;
CREATE TABLE t4 LIKE t2;
INSERT INTO t4 SELECT * FROM t2;
CREATE TABLE t5 (c INT);
INSERT INTO t5 VALUES (1), (2), (3);

--echo # This should show two materialization groups where applicable

let $query=SELECT * FROM t5
  WHERE c IN (SELECT t2.c FROM t1 JOIN t2 ON t2.c_key = t1.c_key)
    AND c IN (SELECT t4.c FROM t3 JOIN t4 ON t4.c_key = t3.c_key);
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query

DROP TABLE t1, t2, t3, t4, t5;

CREATE TABLE t1 (i INT);
CREATE TABLE t2 (i INT);
CREATE TABLE t3 (i INT);

INSERT INTO t1 VALUES (1);
INSERT INTO t2 VALUES (1);
INSERT INTO t3 VALUES (1);

--echo # Subqueries in UPDATE values list

let $query=UPDATE t1 SET i=(SELECT i FROM t2);
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query
let $query=UPDATE t1, t2 SET t1.i=(SELECT i FROM t3);
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query

--echo # INSERT ... ON DUPLICATE KEY UPDATE x=(SELECT ...) value list

let $query=INSERT INTO t1 (i)
             SELECT i FROM t2 ON DUPLICATE KEY UPDATE i=(SELECT i FROM t2);
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query

let $query=INSERT INTO t1 VALUES (1)
             ON DUPLICATE KEY UPDATE i = (SELECT i FROM t2);
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query

--echo # Subqueries in INSERT VALUES tuples:

let $query=INSERT INTO t3 VALUES((SELECT i FROM t1)), ((SELECT i FROM t2));
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query

DROP TABLE t1, t2, t3;

--echo # Various queries

--source include/turn_off_only_full_group_by.inc
let $query=
  SELECT a, b FROM
    (SELECT 1 AS a, 2 AS b
     UNION ALL
     SELECT 1 AS a, 2 AS b) t1
  GROUP BY a
  ORDER BY b DESC;
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query
--source include/restore_sql_mode_after_turn_off_only_full_group_by.inc

--echo #

CREATE TABLE t1(a INT, b INT);
INSERT INTO t1 VALUES (), ();
let $query=SELECT 1 FROM t1 GROUP BY GREATEST(t1.a, (SELECT 1 FROM (SELECT t1.b FROM t1, t1 t2 ORDER BY t1.a, t1.a LIMIT 1) AS d));
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query
DROP TABLE t1;

--echo #

CREATE TABLE t1(f1 INT);
INSERT INTO t1 VALUES (1),(1);
let $query=SELECT 1 FROM t1 WHERE (SELECT (SELECT 1 FROM t1 GROUP BY f1));
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query
DROP TABLE t1;

--echo #

CREATE TABLE t1 (i INT);
CREATE TABLE t2 (i INT, j INT);
INSERT INTO t1 VALUES (1), (2), (3), (4), (5), (6), (7), (8), (9), (10);
INSERT INTO t2 SELECT i, i * 10 FROM t1;
let $query=SELECT * FROM t1 ORDER BY (SELECT t2.j FROM t2 WHERE t2.i = t1.i);
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query
--source include/turn_off_only_full_group_by.inc
let $query=SELECT * FROM t1 GROUP BY (SELECT t2.j FROM t2 WHERE t2.i = t1.i);
--eval EXPLAIN $query
--eval EXPLAIN FORMAT=JSON $query
--source include/restore_sql_mode_after_turn_off_only_full_group_by.inc
DROP TABLE t1, t2;

CREATE TABLE t1 (a INT NOT NULL, b INT NOT NULL, KEY k1 (a, b));
INSERT INTO t1 VALUES (10,1),(10,2),(10,3),(20,4),(20,5),(20,6),
  (30,7),(30,8),(30,9),(40,10),(40,11),(40,12),(40,13),
  (40,14),(40,15),(40,16),(40,17),(40,18),(40,19),(40,20);

EXPLAIN FORMAT=JSON SELECT a, MIN(b) AS b FROM t1 GROUP BY a ORDER BY b;

DROP TABLE t1;

--echo #

CREATE TABLE t1 (a INT NOT NULL, b CHAR(3) NOT NULL, PRIMARY KEY (a)) charset utf8mb4;
INSERT INTO t1 VALUES (1,'ABC'), (2,'EFG'), (3,'HIJ');
CREATE TABLE t2 (a INT NOT NULL,b CHAR(3) NOT NULL,PRIMARY KEY (a, b)) charset utf8mb4;
INSERT INTO t2 VALUES (1,'a'),(1,'b'),(3,'F');

EXPLAIN FORMAT=JSON SELECT t1.a, GROUP_CONCAT(t2.b) AS b FROM t1 LEFT JOIN t2 ON t1.a=t2.a GROUP BY t1.a ORDER BY t1.b;

DROP TABLE t1;
DROP TABLE t2;

--echo #

CREATE TABLE t1 (a INT, b INT);

INSERT INTO t1 VALUES
  (1,4),
  (2,2), (2,2),
  (4,1), (4,1), (4,1), (4,1),
  (2,1), (2,1);

EXPLAIN FORMAT=JSON SELECT SUM(b) FROM t1 GROUP BY a WITH ROLLUP;

DROP TABLE t1;

--echo # Composition of DISTINCT, GROUP BY and ORDER BY

CREATE TABLE t1 (a INT, b INT);
INSERT INTO t1 VALUES (1, 1), (1, 2), (2, 1), (2, 2), (3, 1);

let $query=SELECT DISTINCT SUM(b) s FROM t1 GROUP BY a ORDER BY s;
--eval EXPLAIN FORMAT=JSON $query
FLUSH STATUS;
--eval $query
--disable_warnings
SHOW SESSION STATUS WHERE (Variable_name LIKE 'Sort_%' OR Variable_name LIKE 'Created_%_tables') AND Value > 0;
--enable_warnings

DROP TABLE t1;

--echo # "buffer_result" node

CREATE TABLE t1 (a INT NOT NULL);
CREATE TABLE t2 (a INT NOT NULL, PRIMARY KEY (a));
INSERT INTO t1 VALUES (1);
INSERT INTO t2 VALUES (1),(2);
--source include/turn_off_only_full_group_by.inc
EXPLAIN FORMAT=JSON SELECT SQL_BIG_RESULT DISTINCT t1.a FROM t1,t2 ORDER BY t2.a;
--source include/restore_sql_mode_after_turn_off_only_full_group_by.inc
DROP TABLE t1, t2;

--echo #

CREATE TABLE t1 (a INT NOT NULL, b INT, PRIMARY KEY (a));
CREATE TABLE t2 (a INT NOT NULL, PRIMARY KEY (a));
INSERT INTO t1 VALUES (1,10), (2,20), (3,30),  (4,40);
INSERT INTO t2 VALUES (2), (3), (4), (5);
EXPLAIN FORMAT=JSON SELECT * FROM t2 WHERE t2.a IN (SELECT a FROM t1 WHERE t1.b <> 30);
DROP TABLE t1, t2;

--echo #
--echo # WL#11350 extensions
--echo #
CREATE TABLE r(a INT);
INSERT INTO r VALUES (1), (2), (-1), (-2);
CREATE TABLE s(a INT);
INSERT INTO s VALUES (1), (10), (20), (-10), (-20);
CREATE TABLE t(a INT);
INSERT INTO t VALUES (10), (100), (200), (-100), (-200);
ANALYZE TABLE r,s,t;

--echo # Test nesting structures
let $query =
         ( ( SELECT * FROM r UNION
             (SELECT * FROM s ORDER BY a LIMIT 1)) UNION
           ( SELECT * FROM s UNION SELECT 2 LIMIT 3)
            ORDER BY 1 LIMIT 3)
         ORDER BY 1;

eval EXPLAIN FORMAT=json $query;
--echo # For comparison
--replace_regex $elide_costs
eval EXPLAIN FORMAT=tree $query;

--echo # Test no result if no materializaton
EXPLAIN FORMAT=json SELECT 1 UNION ALL SELECT 2;

--echo # Used to not show sorting before WL#11350
EXPLAIN FORMAT=json (SELECT a FROM r LIMIT 2) ORDER BY 1;

EXPLAIN FORMAT=json ((SELECT a FROM t ORDER BY 1 limit 3) ORDER BY -a limit 2) order by a;

--echo # Test big one
let $query =
     (SELECT * FROM r
      UNION SELECT * FROM s);
let $1=200;
while ($1)
{
 let $query =
     ($query
      UNION SELECT * FROM s);
 dec $1;
}

--echo # This query has max nesting and should work
eval EXPLAIN FORMAT=json $query;

--echo #
--echo # INTERSECT operator
--echo #
let $query = SELECT * FROM r INTERSECT SELECT * FROM s;

eval EXPLAIN FORMAT = json $query;

let $query = SELECT * FROM r INTERSECT ALL SELECT * FROM s;
eval EXPLAIN FORMAT = json $query;

--echo #
--echo # EXCEPT operator
--echo #
let $query = SELECT * FROM r EXCEPT SELECT * FROM s;

eval EXPLAIN FORMAT = json $query;

let $query = SELECT * FROM r EXCEPT ALL SELECT * FROM s;
eval EXPLAIN FORMAT = json $query;

DROP TABLE r, s, t;

--echo #
--echo # Bug#34463119 WL#349 Assertion `current_context->type == CTX_JOIN || ..
--echo #              at opt_explain_json.cc
--echo #
CREATE TABLE t(pk int NOT NULL AUTO_INCREMENT, PRIMARY KEY (pk));

EXPLAIN FORMAT=JSON
SELECT * FROM (SELECT * FROM t) AS alias1
              JOIN
              t AS alias2
WHERE alias1.pk NOT IN (SELECT 2 INTERSECT SELECT 1) AND
      alias1.pk = 105;
DROP TABLE t;

--echo #
--echo #  WL#15684 System variable to select JSON EXPLAIN format
--echo #
SET @saved_json_format_version = @@explain_json_format_version;
SET @@end_markers_in_json=OFF;
SET @@explain_json_format_version = 1;

CREATE TABLE t (i INT);
INSERT INTO t VALUES (1), (2), (3);
ANALYZE TABLE t;

EXPLAIN FORMAT=JSON SELECT * FROM t WHERE i IN (2, 3) LIMIT 1;

SET @@explain_json_format_version = 2;

EXPLAIN FORMAT=JSON SELECT * FROM t WHERE i IN (2, 3) LIMIT 1;

SET @@explain_json_format_version = 1;

DELIMITER |;
--echo # Check changing system variable in stored procedure works as expected.
# First and third EXPLAIN use the session value for explain_json_format_version from when the procedure was prepared.
# Second and fourth EXPLAIN use the session value for explain_json_format_version from the first PREPARE.
# Fifth EXPLAIN uses the passed json_format_version value for explain_json_format_version.
# JSON format version 2 contains a top level "query" field that version 1 does not.
CREATE PROCEDURE p (json_format_version INT) BEGIN
  EXPLAIN FORMAT=JSON INTO @v1 SELECT * FROM t WHERE i IN (2, 3) LIMIT 1;
  SELECT JSON_CONTAINS_PATH(@v1, 'one', '$.query') + 1 AS explain_json_format_version;

  SET @stmt_txt = 'EXPLAIN FORMAT=JSON INTO @v1 SELECT * FROM t WHERE i IN (2, 3) LIMIT 1';
  PREPARE stmt FROM @stmt_txt;
  EXECUTE stmt;
  SELECT JSON_CONTAINS_PATH(@v1, 'one', '$.query') + 1 AS explain_json_format_version;

  SET @@explain_json_format_version = json_format_version;
  EXPLAIN FORMAT=JSON INTO @v1 SELECT * FROM t WHERE i IN (2, 3) LIMIT 1;
  SELECT JSON_CONTAINS_PATH(@v1, 'one', '$.query') + 1 AS explain_json_format_version;

  EXECUTE stmt;
  SELECT JSON_CONTAINS_PATH(@v1, 'one', '$.query') + 1 AS explain_json_format_version;

  PREPARE stmt FROM @stmt_txt;
  EXECUTE stmt;
  SELECT JSON_CONTAINS_PATH(@v1, 'one', '$.query') + 1 AS explain_json_format_version;
END|
DELIMITER ;|

SET @@explain_json_format_version = 2;

# Expect the system variable to be set by the procedure.
CALL p(1);
SELECT @@explain_json_format_version;
CALL p(2);
SELECT @@explain_json_format_version;

DROP PROCEDURE p;
DROP TABLE t;
SET @@end_markers_in_json=ON;
SET @@explain_json_format_version = @saved_json_format_version;

--echo #
--echo # Bug#36134568 Add query type to iterator-based EXPLAIN FORMAT=JSON
--echo #

SET @saved_json_format_version = @@explain_json_format_version;
SET @@explain_json_format_version = 2;

CREATE TABLE t1 (i1 INT PRIMARY KEY, i2 INT);
CREATE TABLE t2 (i3 INT, i4 INT);
INSERT INTO t1 VALUES (1,2), (2,3), (3,4);
INSERT INTO t2 SELECT i2, i1 FROM t1;
ANALYZE TABLE t1, t2;

EXPLAIN FORMAT=JSON INTO @v1 SELECT * FROM t1 JOIN t2 ON i1 = i3 WHERE i2 = 2;
SELECT JSON_EXTRACT(@v1, '$.query_type') = 'select';

SET @v1 = NULL;

EXPLAIN FORMAT=JSON INTO @v1 SELECT * FROM t1;
SELECT JSON_EXTRACT(@v1, '$.query_type') = 'select';

SET @v1 = NULL;

EXPLAIN FORMAT=JSON INTO @v1 INSERT INTO t1 VALUES (4,5);
SELECT JSON_EXTRACT(@v1, '$.query_type') = 'insert';

SET @v1 = NULL;

EXPLAIN FORMAT=JSON INTO @v1 INSERT INTO t1 SELECT * FROM t2;
SELECT JSON_EXTRACT(@v1, '$.query_type') = 'insert';

SET @v1 = NULL;

EXPLAIN FORMAT=JSON INTO @v1 UPDATE t1 SET i2 = i2 + 1 WHERE i1 = 1;
SELECT JSON_EXTRACT(@v1, '$.query_type') = 'update';

SET @v1 = NULL;

EXPLAIN FORMAT=JSON INTO @v1 REPLACE t1 SELECT * FROM t2;
SELECT JSON_EXTRACT(@v1, '$.query_type') = 'replace';

SET @v1 = NULL;

EXPLAIN FORMAT=JSON INTO @v1 DELETE FROM t1;
SELECT JSON_EXTRACT(@v1, '$.query_type') = 'delete';

SET @v1 = NULL;

EXPLAIN FORMAT=JSON INTO @v1 UPDATE t1, t2 SET i1 = i1 - 1, i3 = i3 + 1;
SELECT JSON_EXTRACT(@v1, '$.query_type') = 'update';

SET @v1 = NULL;

EXPLAIN FORMAT=JSON INTO @v1 DELETE t1, t2 FROM t1, t2;
SELECT JSON_EXTRACT(@v1, '$.query_type') = 'delete';

DROP TABLE t1, t2;
SET @v1=NULL;
SET @@explain_json_format_version = @saved_json_format_version;

--echo #
--echo # Bug#37126176 Add lookup references to iterator-based EXPLAIN FORMAT=JSON for index lookups
--echo #

SET @saved_json_format_version = @@explain_json_format_version;
SET @@explain_json_format_version = 2;

SET @v1 = NULL;
CREATE TABLE t (pk INT PRIMARY KEY AUTO_INCREMENT, i INT DEFAULT NULL, INDEX idx(i));
INSERT INTO t(i) VALUES (3), (2), (1), (NULL);
ANALYZE TABLE t;

# Even though these plans are mostly pretty simple we use JSON functions to
# extract the relevant paths from the EXPLAIN output in case the plan should
# change in the future but still contains the desired path.
# As long as the EXPLAIN output contains the desired fields and values in the
# right relative position we do not care about other parts of the plan.

# CONCAT(SUBSTRING_INDEX(path, '.', CHAR_LENGTH - CHAR_LENGTH)) extracts the
# path to the lookup object found with the JSON_SEARCH.
# The same effect could probably be achieved with
# JSON_EXTRACT(@v1, '$**.lookup_references[0]'), but this way we make sure the
# access type is right and from the right object.
# This is probably more useful with more complex plans.

--echo # Index lookup shows correct reference type in "lookup_references".
# Index lookup (REF)
EXPLAIN FORMAT=JSON INTO @v1 SELECT i FROM t WHERE i = 1;
SELECT JSON_EXTRACT(@v1,
  CONCAT(
    SUBSTRING_INDEX(index_access_type_path, '.',
      CHAR_LENGTH(index_access_type_path)
        -
      CHAR_LENGTH(REPLACE(index_access_type_path, '.', ''))),
    '.lookup_references[0]'))
  = "const"
  AS index_lookup_references_const
FROM (SELECT JSON_UNQUOTE(JSON_SEARCH(@v1, 'one', 'index_lookup')) AS index_access_type_path) AS t;

SET @v1 = NULL;

# Single-row index lookup (EQ_REF)
EXPLAIN FORMAT=JSON INTO @v1 SELECT t1.pk FROM t t1, t t2 WHERE t1.pk = t2.pk + 1;
SELECT JSON_EXTRACT(@v1,
  CONCAT(
    SUBSTRING_INDEX(index_access_type_path, '.',
      CHAR_LENGTH(index_access_type_path)
        -
      CHAR_LENGTH(REPLACE(index_access_type_path, '.', ''))),
    '.lookup_references[0]'))
  = "func"
  AS index_lookup_references_func
FROM (SELECT JSON_UNQUOTE(JSON_SEARCH(@v1, 'one', 'index_lookup')) AS index_access_type_path) AS t;

SET @v1 = NULL;

# Single-row index lookup (EQ_REF)
# "lookup_references" can be either '["test.t1.pk"]' or '["test.t2.pk"]'.
# If the plan changes we do not care as long as "lookup_references" contains a
# fully qualified column name.
EXPLAIN FORMAT=JSON INTO @v1 SELECT t1.pk FROM t t1, t t2 WHERE t1.pk = t2.pk;
SELECT JSON_EXTRACT(@v1,
  CONCAT(
    SUBSTRING_INDEX(index_access_type_path, '.',
      CHAR_LENGTH(index_access_type_path)
        -
      CHAR_LENGTH(REPLACE(index_access_type_path, '.', ''))),
    '.lookup_references[0]'))
  IN ("test.t1.pk", "test.t2.pk")
  AS index_lookup_references_column
FROM (SELECT JSON_UNQUOTE(JSON_SEARCH(@v1, 'one', 'index_lookup')) AS index_access_type_path) AS t;

SET @v1 = NULL;

# Index lookup (REF_OR_NULL)
EXPLAIN FORMAT=JSON INTO @v1 SELECT * FROM t WHERE i = 1 OR i IS NULL;
SELECT JSON_UNQUOTE(JSON_EXTRACT(@v1,
  CONCAT(
    SUBSTRING_INDEX(index_access_type_path, '.',
      CHAR_LENGTH(index_access_type_path)
        -
      CHAR_LENGTH(REPLACE(index_access_type_path, '.', ''))),
    '.lookup_condition')))
  LIKE "% or NULL"
  AS is_ref_or_null
FROM (SELECT JSON_UNQUOTE(JSON_SEARCH(@v1, 'one', 'index_lookup')) AS index_access_type_path) AS t;

SET @v1 = NULL;

# Multi-range read (MRR)
SET @saved_optimizer_switch = @@optimizer_switch;
SET optimizer_switch='batched_key_access=on,mrr=on,mrr_cost_based=off';

EXPLAIN FORMAT=JSON INTO @v1 SELECT /*+ BKA(t2) */ * FROM t t1 LEFT JOIN t t2 ON t1.pk = t2.pk AND t1.i = 1 AND t1.i = 2;
SELECT JSON_EXTRACT(@v1,
  CONCAT(
    SUBSTRING_INDEX(index_access_type_path, '.',
      CHAR_LENGTH(index_access_type_path)
        -
      CHAR_LENGTH(REPLACE(index_access_type_path, '.', ''))),
    '.lookup_references')) IS NOT NULL
  AS mrr_has_lookup_references
FROM (SELECT JSON_UNQUOTE(JSON_SEARCH(@v1, 'one', 'multi_range_read')) AS index_access_type_path) AS t;

SET optimizer_switch = @saved_optimizer_switch;

SET @v1 = NULL;
DROP TABLE t;

# Fulltext search (FULLTEXT)
--echo # Fulltext search has "lookup_references", should only show "const"
CREATE TABLE t (a VARCHAR(200), b TEXT, FULLTEXT (a,b)) ENGINE = InnoDB charset utf8mb4;
INSERT INTO t VALUES  ('This is a sample text', 'I made up for this test.'),
                      ('We want to show that fulltext', 'search references a constant in the "lookup_condition".'),
                      ('In this test the EXPLAIN output', 'should contain a field called "lookup_references".'),
                      ('"lookup_references" should be an array.', 'That array should contain an element that is "const".'),
                      ('Function MATCH ... AGAINST()','is used to do a fulltext search.'),
                      ('Fulltext searches in MySQL', 'are confusing.');
ANALYZE TABLE t;

EXPLAIN FORMAT=JSON INTO @v1 SELECT * FROM t WHERE MATCH(a,b) AGAINST ("fulltext");
SELECT JSON_EXTRACT(@v1,
  CONCAT(
    SUBSTRING_INDEX(index_access_type_path, '.',
      CHAR_LENGTH(index_access_type_path)
        -
      CHAR_LENGTH(REPLACE(index_access_type_path, '.', ''))),
    '.lookup_references[0]'))
  = "const"
  AS fulltext_search_references_const
FROM (SELECT JSON_UNQUOTE(JSON_SEARCH(@v1, 'one', 'full_text_search')) AS index_access_type_path) AS t;

SET @v1 = NULL;
DROP TABLE t;

SET @@explain_json_format_version = @saved_json_format_version;

--echo #
--echo # Bug#35239659 Separate query attributes and iterator attributes in iterator-based EXPLAIN JSON
--echo #
# Not many tests for this since it is tested every time the full JSONv2 format
# is printed in a test

SET @saved_json_format_version = @@explain_json_format_version;
SET @@explain_json_format_version = 2;

CREATE TABLE t (i INT);
# Simple TREE EXPLAIN to show TREE output is not affected
EXPLAIN FORMAT=TREE SELECT * FROM t t1 JOIN t t2 WHERE t1.i = t2.i;

EXPLAIN FORMAT=JSON INTO @var SELECT * FROM t t1 JOIN t t2 WHERE t1.i = t2.i;
SELECT JSON_KEYS(@var);

DROP TABLE t;
SET @var = NULL;

SET @@explain_json_format_version = @saved_json_format_version;