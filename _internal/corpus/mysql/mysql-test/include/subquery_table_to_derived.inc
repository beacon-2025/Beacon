--source include/elide_costs.inc

--echo # WL#13425 Transform IN and EXISTS predicates for RAPID
# It's named subquery_table_to_derived.test, because
# the subquery to the right of IN, EXISTS, is called a "table subquery"
# (as opposed to a "scalar subquery").
# A reduced adaptation of this test to RAPID is in rapid.subquery_table_to_derived.

SET OPTIMIZER_SWITCH="subquery_to_derived=on";

CREATE TABLE t1 (a INT, b INT);
INSERT INTO t1 VALUES(1,10),(2,20),(3,30);

CREATE TABLE t2 (a INT, b INT);
INSERT INTO t2 VALUES(1,10),(2,20),(3,30),(1,110),(2,120),(3,130);

# Add more rows to make sure we get consistent plans. Otherwise table scan path
# is chosen for the materialized temp table as against ref access path, and
# this in turn leads to some plans being different on at least one platform,
# namely Mac.
INSERT INTO t2 SELECT * FROM t2;
INSERT INTO t2 SELECT * FROM t2;
INSERT INTO t2 SELECT * FROM t2;


ANALYZE TABLE t1,t2;

# IN

let $query=
SELECT * FROM t1 ot
WHERE ot.b<0 OR ot.a IN (SELECT it.a+1 FROM t2 it);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

# Test optimizer_switch

SET OPTIMIZER_SWITCH="subquery_to_derived=off";
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;
SET OPTIMIZER_SWITCH="subquery_to_derived=on";

# IN with two identically-named expressions in SELECT list:
# the renaming of expressions is meant to disambiguate
# them when moved to the derived table, which is necessary to:
# - have a working table
# - have correct LEFT JOIN equalities.
# We also have two identical expressions in SELECT list and
# WHERE.

let $query=
SELECT * FROM t1 ot
WHERE ot.b<0 OR (ot.a,ot.a+1,ot.a+2)
 IN (SELECT it.a+1 AS myname,it.a+2 AS myname,it.a+3 FROM t2 it
     WHERE it.a+3=ot.a+2);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

# Decorrelated EXISTS(SELECT *)

let $query=
SELECT * FROM t1 ot
WHERE ot.b<0 OR EXISTS(SELECT * FROM t2 it WHERE ot.a=it.a+1);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

# Decorrelated EXISTS(SELECT columns)

# Substituting the selected expressions with constants matters for not
# emitting duplicates

let $query=
SELECT * FROM t1 ot
WHERE ot.b<0 OR EXISTS(SELECT it.b FROM t2 it WHERE ot.a=it.a+1);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

# And also for removing superfluous correlation of the SELECT list

let $query=
SELECT * FROM t1 ot
WHERE ot.b<0 OR EXISTS(SELECT it.b,ot.b FROM t2 it WHERE ot.a=it.a+1);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

# If using a view, PS makes it more tricky: when 2nd resolution starts, the "1"
# which was put in the SELECT list of EXISTS, is overwritten by
# rollback_item_tree_changes(); verify that we put "1" again:
CREATE view v2 AS SELECT * FROM t2;
PREPARE s FROM
"SELECT * FROM t1 ot
WHERE ot.b<0 OR EXISTS(SELECT it.b FROM v2 it WHERE ot.a=it.a+1)";
EXECUTE s;

# IN deep inside AND/ORs

let $query=
SELECT * FROM t1 ot
WHERE ot.b<0 OR (ot.b<0 AND (ot.b<0 OR ot.a IN (SELECT it.a+1 FROM t2 it)));
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

# For code coverage: when we decorrelate, and the subquery contains a
# derived table:

let $query=
SELECT * FROM t1 ot
WHERE ot.b<0 OR ot.a IN (SELECT it.a+1 FROM (SELECT * FROM t2 LIMIT 1) it
                         WHERE it.a+3=ot.a+1);
--replace_regex $elide_costs
eval EXPLAIN $query;

# Single-table UPDATE: we can transform the subquery to derived, by first
# converting to multi-table UPDATE.

BEGIN;

let $query=
UPDATE t1 ot SET a=a*100
WHERE ot.b<0 OR ot.a IN (SELECT it.a+1 FROM t2 it);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

SELECT * FROM t1;

# Undo the above
ROLLBACK;

# Multi-table UPDATE

BEGIN;

let $query=
UPDATE t1 ot, (SELECT 1) AS dummy
SET a=a*100
WHERE ot.b<0 OR ot.a IN (SELECT it.a+1 FROM t2 it);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

SELECT * FROM t1;
ROLLBACK;

# Single-table DELETE

BEGIN;

let $query=
DELETE FROM t1 ot
WHERE ot.b<0 OR ot.a IN (SELECT it.a+1 FROM t2 it);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

SELECT * FROM t1;
ROLLBACK;

# Multi-table DELETE

BEGIN;
let $query=
DELETE ot.* FROM t1 ot, (SELECT 1) AS dummy
WHERE ot.b<0 OR ot.a IN (SELECT it.a+1 FROM t2 it);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;

SELECT * FROM t1;
ROLLBACK;

# Same, in a SP

CREATE PROCEDURE del()
DELETE ot.* FROM t1 ot, (SELECT 1) AS dummy
WHERE ot.b<0 OR ot.a IN (SELECT it.a+1 FROM t2 it);

SELECT * FROM t1;

BEGIN;
CALL del();
SELECT * FROM t1;
ROLLBACK;

BEGIN;
CALL del();
SELECT * FROM t1;
ROLLBACK;

SELECT * FROM t1;
DROP PROCEDURE del;

--echo # Testing WL#12885 together with WL#13425

--echo # WL#12885 with semijoin:
--replace_regex $elide_costs
EXPLAIN SELECT * FROM t1 WHERE (SELECT SUM(a) FROM t1) IN (SELECT b FROM t1);
--echo # WL#12885 with WL#13425:
--echo # Scalar subquery as left expr
--replace_regex $elide_costs
EXPLAIN SELECT * FROM t1 WHERE (SELECT SUM(a) FROM t1) IN (SELECT b FROM t1) OR a>3;
--echo # Scalar subquery as right expr
--replace_regex $elide_costs
EXPLAIN SELECT * FROM t1 WHERE 36 IN (SELECT (SELECT SUM(a) FROM t1)+b FROM t1) OR a>3;
--echo # Scalar subquery in EXISTS
--replace_regex $elide_costs
EXPLAIN SELECT * FROM t1 WHERE EXISTS (SELECT * FROM t1 WHERE (SELECT SUM(a) FROM t1)=b) OR a>3;
--echo # Scalar subquery in NOT EXISTS
--replace_regex $elide_costs
EXPLAIN SELECT * FROM t1 WHERE NOT EXISTS (SELECT * FROM t1 WHERE (SELECT SUM(a) FROM t1)>b) OR a>3;
--echo # Scalar subquery in NOT IN and non-nullables (antijoin)
--replace_regex $elide_costs
EXPLAIN SELECT * FROM t1 WHERE 36 NOT IN (SELECT COALESCE((SELECT SUM(a) FROM t1),b,55) FROM t1) OR a>3;

DROP TABLE t1,t2;
DROP view v2;

--echo # Bug#30697743 WL#13425: ASSERT: !THD->IS_ERROR()' IN SELECT_LEX::PREPARE() AT SQL/SQL_RESOLVE

CREATE TABLE t1 (col_varchar_key VARCHAR(1));
--error ER_TRUNCATED_WRONG_VALUE
CREATE TABLE t2
SELECT 1 FROM t1 WHERE
col_varchar_key IN (SELECT  1 FROM t1
                    WHERE ('f', 'f') IN (SELECT 1, COUNT(1) FROM t1));
DROP TABLE t1;

--echo # Bug#30709889 ASSERT: &SUBS_SELECT->FIELDS_LIST == &SUBS_SELECT->ITEM_LIST && SUBS_SELECT->IT

CREATE TABLE t1 (
  field2 VARCHAR(2),
  field3 BIGINT
);

CREATE TABLE t2 (
  col_int INT,
  pk INT
);

SELECT 1 FROM t1
WHERE (field2 ,field3) IN
(
 SELECT STRAIGHT_JOIN
        1 AS field2 ,
        ( SELECT 1 AS SQ1_field1 FROM t2 AS SQ1_alias1
          WHERE SQ1_alias1.col_int != alias1.pk) AS field3
 FROM t2 AS alias1 GROUP BY field2,field3
);

DROP TABLE t2,t1;

--echo # Bug#31018642 RESULT MISMATCHES BETWEEN TRUNK & WORKLOG
--echo # Verify that <> is decorrelated inside an AND-ed negated predicate

# we must block semijoin to test the conversion to derived table
SET OPTIMIZER_SWITCH="semijoin=off";

CREATE TABLE t1(a INT);
CREATE TABLE t2(b INT);
INSERT INTO t1 VALUES(1);
INSERT INTO t2 VALUES(2),(3);
ANALYZE TABLE t1,t2;
let $query=
SELECT * FROM t1
  WHERE NOT EXISTS(SELECT * FROM t2 WHERE t1.a<>t2.b);
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;
# With OR, a<>b is not decorrelated
let $query=
SELECT * FROM t1
  WHERE NOT EXISTS(SELECT * FROM t2 WHERE t1.a<>t2.b) OR t1.a>0;
--error ER_SUBQUERY_TRANSFORM_REJECTED
eval EXPLAIN $query;
# With AND, a<>b is decorrelated
let $query=
SELECT * FROM t1
    WHERE NOT EXISTS(SELECT * FROM t2 WHERE t1.a<>t2.b) AND t1.a>0;
--replace_regex $elide_costs
eval EXPLAIN $query;
eval $query;
# Without negation it is not
--error ER_SUBQUERY_TRANSFORM_REJECTED
EXPLAIN
SELECT * FROM t1
    WHERE EXISTS(SELECT * FROM t2 WHERE t1.a<>t2.b) AND t1.a>0;

--echo # Verify that >=, <=, >, < are also decorrelated.

--replace_regex $elide_costs
EXPLAIN
SELECT * FROM t1
    WHERE NOT EXISTS(SELECT * FROM t2 WHERE t1.a>=t2.b) AND t1.a>0;
--replace_regex $elide_costs
EXPLAIN
SELECT * FROM t1
    WHERE NOT EXISTS(SELECT * FROM t2 WHERE t1.a>t2.b) AND t1.a>0;
--replace_regex $elide_costs
EXPLAIN
SELECT * FROM t1
    WHERE NOT EXISTS(SELECT * FROM t2 WHERE t1.a<=t2.b) AND t1.a>0;
--replace_regex $elide_costs
EXPLAIN
SELECT * FROM t1
    WHERE NOT EXISTS(SELECT * FROM t2 WHERE t1.a<t2.b) AND t1.a>0;
--echo # Reverse the order of arguments:
--replace_regex $elide_costs
EXPLAIN
SELECT * FROM t1
    WHERE NOT EXISTS(SELECT * FROM t2 WHERE t2.b<t1.a) AND t1.a>0;

DROP TABLE t1,t2;
SET OPTIMIZER_SWITCH="semijoin=on";

--echo #
--echo # Bug #31941934: WL#14071: ASSERTION `JOIN == NULLPTR' FAILED|SQL/SQL_SELECT.CC
--echo #

CREATE TABLE t1 ( pk INTEGER );
CREATE TABLE t2 ( a INTEGER );
CREATE TABLE t3 ( b INTEGER );

# subquery_to_derived adds a DISTINCT to this query,
# which the hypergraph optimizer can't handle yet.
# It should error out and be properly skipped, instead of
# being treated as false and then crashing on re-optimize.
SELECT *
  FROM t1 LEFT JOIN t2 ON 2 IN (
    SELECT COUNT(*) FROM t1
    WHERE NOT EXISTS ( SELECT b FROM t3 )
    GROUP BY pk
  );

DROP TABLE t1, t2, t3;

--echo #
--echo # Bug#35014318 Exists query assertion error
--echo # Bug#34746261 Forced secondary engine execution assertion error
--echo #
--echo # This issue showed deficiencies with table value constructor
--echo # when used in a [NOT] EXISTS subquery
CREATE TABLE t1 (c0 INT);
INSERT INTO t1 VALUES (1), (2);
ANALYZE TABLE t1;

SELECT 1 FROM t1 WHERE NOT EXISTS (VALUES ROW(1),ROW(2));
SELECT c0 FROM t1 WHERE NOT EXISTS (VALUES ROW(1),ROW(2));

SELECT 1 FROM t1 WHERE EXISTS (VALUES ROW(1),ROW(2));
SELECT c0 FROM t1 WHERE EXISTS (VALUES ROW(1),ROW(2));

SELECT 1 FROM (SELECT 5) t1(c0) WHERE EXISTS (VALUES ROW(1),ROW(2));

--echo # This will do the transform in spite of the presence of
--echo # LIMIT/OFFSET since we can compute at prepare time whether the
--echo # result set will be empty or not
SELECT c0 FROM t1 WHERE EXISTS (VALUES ROW(1),ROW(2) LIMIT 1 OFFSET 0);
SELECT c0 FROM t1 WHERE EXISTS (VALUES ROW(1),ROW(2) LIMIT 1 OFFSET 1);
SELECT c0 FROM t1 WHERE EXISTS (VALUES ROW(1),ROW(2) LIMIT 1 OFFSET 2);
SELECT c0 FROM t1 WHERE EXISTS (VALUES ROW(1),ROW(2) LIMIT 0);
SELECT c0 FROM t1 WHERE EXISTS (VALUES ROW(1),ROW(2) LIMIT 1);

--echo # This does not use semi-join since we can't short-circuit due
--echo # to dynamic parameter. Also fixed assert error due to missing
--echo # type for ? (not transform dependent).
PREPARE p FROM 'SELECT c0 FROM t1
                WHERE EXISTS (VALUES ROW(1),ROW(2) LIMIT 1 OFFSET ?)';

SET @n=0;
EXECUTE p USING @n;

SET @n=1;
EXECUTE p USING @n;

SET @n=2;
EXECUTE p USING @n;

PREPARE p FROM 'SELECT c0 FROM t1 WHERE EXISTS (VALUES ROW(1),ROW(2) LIMIT ?)';
SET @n=0;
EXECUTE p USING @n;

SET @n=1;
EXECUTE p USING @n;

DROP PREPARE p;

DROP TABLE t1;

--echo # Bug#35804794: mysqld assertion failure in
--echo #               Query_block::replace_subquery_in_expr

CREATE TABLE t1 (col varchar(1) CHARACTER SET ASCII);

SELECT col
FROM t1
WHERE col >= (SELECT MAX(CONCAT('å' COLLATE utf8mb4_la_0900_as_cs)) FROM t1);

DROP TABLE t1;
