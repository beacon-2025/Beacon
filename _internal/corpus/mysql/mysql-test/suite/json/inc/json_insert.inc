--echo # Test of the JSON data type.
--echo # ----------------------------------------------------------------------

SET NAMES utf8mb3;

CREATE TABLE t1 (i INT, j JSON) CHARSET utf8mb4;
SHOW CREATE TABLE t1;
INSERT INTO t1 VALUES (0, NULL);
INSERT INTO t1 VALUES (1, '{"a": 2}');
INSERT INTO t1 VALUES (2, '[1,2]');
INSERT INTO t1 VALUES (3, '{"a":"b", "c":"d","ab":"abc", "bc": ["x", "y"]}');
INSERT INTO t1 VALUES (4, '["here", ["I", "am"], "!!!"]');
INSERT INTO t1 VALUES (5, '"scalar string"');
INSERT INTO t1 VALUES (6, 'true');
INSERT INTO t1 VALUES (7, 'false');
INSERT INTO t1 VALUES (8, 'null');
INSERT INTO t1 VALUES (9, '-1');
INSERT INTO t1 VALUES (10, CAST(CAST(1 AS UNSIGNED) AS JSON));
INSERT INTO t1 VALUES (11, '32767');
INSERT INTO t1 VALUES (12, '32768');
INSERT INTO t1 VALUES (13, '-32768');
INSERT INTO t1 VALUES (14, '-32769');
INSERT INTO t1 VALUES (15, '2147483647');
INSERT INTO t1 VALUES (16, '2147483648');
INSERT INTO t1 VALUES (17, '-2147483648');
INSERT INTO t1 VALUES (18, '-2147483649');
INSERT INTO t1 VALUES (19, '18446744073709551615');
INSERT INTO t1 VALUES (20, '18446744073709551616');
INSERT INTO t1 VALUES (21, '3.14');
INSERT INTO t1 VALUES (22, '{}');
INSERT INTO t1 VALUES (23, '[]');
INSERT INTO t1 VALUES (24, CAST(CAST('2015-01-15 23:24:25' AS DATETIME) AS JSON));
INSERT INTO t1 VALUES (25, CAST(CAST('23:24:25' AS TIME) AS JSON));
INSERT INTO t1 VALUES (26, CAST(CAST('2015-01-15' AS DATE) AS JSON));
INSERT INTO t1 VALUES (27, CAST(TIMESTAMP'2015-01-15 23:24:25' AS JSON));
INSERT INTO t1 VALUES (28, CAST(ST_GeomFromText('POINT(1 1)') AS JSON));
# auto-convert to utf8mb4
INSERT INTO t1 VALUES (29, CAST('[]' AS CHAR CHARACTER SET 'ascii'));
INSERT INTO t1 VALUES (30, CAST(x'cafe' AS JSON));
INSERT INTO t1 VALUES (31, CAST(x'cafebabe' AS JSON));

# Maximum allowed key length is 64k-1
INSERT INTO t1 VALUES (100, CONCAT('{"', REPEAT('a', 64 * 1024 - 1), '":123}'));
--error ER_JSON_KEY_TOO_BIG
INSERT INTO t1 VALUES (101, CONCAT('{"', REPEAT('a', 64 * 1024), '":123}'));
--error ER_JSON_KEY_TOO_BIG
INSERT INTO t1 VALUES (102, CAST(CONCAT('{"', REPEAT('a', 64 * 1024), '":123}') AS JSON));

SELECT i, LENGTH(j), j FROM t1 ORDER BY i;

CREATE TABLE auxtbl(ts TIMESTAMP);
INSERT INTO auxtbl VALUES ('2015-02-24 18:52:00');

--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES ('');
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES ('[');
--error ER_INVALID_JSON_CHARSET
INSERT INTO t1(j) VALUES (x'cafebabe');
--error ER_INVALID_JSON_CHARSET
INSERT INTO t1(j) VALUES (ST_GeomFromText('POINT(1 1)'));
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES (-1);
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES (CAST(1 AS UNSIGNED));
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES (3.14);
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES (3.14E30);
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES (PI());
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) select ts from auxtbl;
DROP TABLE auxtbl;
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES (CAST('15:52:00' as TIME));
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES (CAST('2015-02-24' as DATE));
--error ER_INVALID_JSON_TEXT
INSERT INTO t1(j) VALUES (TIMESTAMP '2015-02-24 15:52:00');

--echo # ----------------------------------------------------------------------
--echo # INSERT using prepared statement (PS)
--echo # ----------------------------------------------------------------------
create table pt1(j json);
create table pt2(j json);

set @a=123;
set @b='123';
set @c=3.14;
set @d=3.14E1;
set @e='"123"';
set @f='2010-12-01 18:44:25';
set @g=null;

prepare ps1 from 'insert into pt1 values (cast(? as json))';
execute ps1 using @a;

prepare ps1 from 'insert into pt1 values (cast(? as json))';
execute ps1 using @b;

prepare ps1 from 'insert into pt1 values (cast(? as json))';
execute ps1 using @c;

prepare ps1 from 'insert into pt1 values (cast(? as json))';
execute ps1 using @d;

prepare ps1 from 'insert into pt1 values (cast(? as json))';
execute ps1 using @e;

prepare ps1 from 'insert into pt1 values (cast(? as json))';
--error ER_INVALID_JSON_TEXT_IN_PARAM
execute ps1 using @f;

prepare ps1 from 'insert into pt1 values (cast(? as json))';
execute ps1 using @g;

prepare ps2 from 'insert into pt2 values (?)';
--error ER_INVALID_JSON_TEXT
execute ps2 using @a;

prepare ps2 from 'insert into pt2 values (?)';
execute ps2 using @b;

prepare ps2 from 'insert into pt2 values (?)';
--error ER_INVALID_JSON_TEXT
execute ps2 using @c;

prepare ps2 from 'insert into pt2 values (?)';
--error ER_INVALID_JSON_TEXT
execute ps2 using @d;

prepare ps2 from 'insert into pt2 values (?)';
execute ps2 using @e;

prepare ps2 from 'insert into pt2 values (?)';
--error ER_INVALID_JSON_TEXT
execute ps2 using @f;

prepare ps2 from 'insert into pt2 values (?)';
execute ps2 using @g;

select json_type(j), j from pt1 order by j;
select json_type(j), j from pt2 order by j;

delete from pt1;
delete from pt2;

# Check different character sets
set @string_utf8=CONVERT(x'616263C3A6C3B8C3A578797A' USING utf8mb4);
set @json_utf8=CONCAT('{"label" : "', @string_utf8, '"}');
set @json_latin1=CONVERT(@json_utf8 USING LATIN1);
select @string_utf8, @json_utf8, @json_latin1;

execute ps1 using @json_utf8;
execute ps1 using @json_latin1;
execute ps2 using @json_utf8;
execute ps2 using @json_latin1;

set @string_ucs2=_ucs2 0x0627064A0631062706460650;
# What to expect when reading from the JSON column:
select HEX(CONVERT(@string_ucs2 USING utf8mb4));
set @json_ucs2=CONCAT('{"label" : "', @string_ucs2, '"}');
# Check it's a UCS2 string:
select collation(@json_ucs2);

# insert:
execute ps1 using @json_ucs2;
execute ps2 using @json_ucs2;

# and read:
select hex(j->>"$.label") from pt1 order by (j->>"$.label");
select hex(j->>"$.label") from pt2 order by (j->>"$.label");

drop prepare ps1;
drop prepare ps2;
drop table pt1;
drop table pt2;
drop table t1;

--echo #
--echo # Bug#26867509: JSON_OBJECT CREATES INVALID JSON CODE
--echo #

CREATE TABLE t1(i INT, KEY(i));
INSERT INTO t1 VALUES (1), (2), (3);
CREATE TABLE t2(i INT, vc VARCHAR(100));
INSERT INTO t2 SELECT i, JSON_ARRAY(i) FROM t1 GROUP BY i;
SELECT * FROM t2 ORDER BY i;
DROP TABLE t1, t2;
