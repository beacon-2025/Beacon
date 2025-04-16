\c
\c -
\c mydatabase
\c mydatabase myuser
\c mydatabase myuser@myhost 5433

CREATE OR REPLACE FUNCTION assert_not_admin() RETURNS void AS $$
BEGIN
	ASSERT current_user <> 'postgres', 'Current user is an admin.';
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION priv_testfunc4(boolean) RETURNS text
  AS 'select col1 from atest2 where col2 = $1;'
  LANGUAGE sql SECURITY DEFINER;

SELECT 1;

CREATE PROCEDURE priv_testproc1(int) AS 'select $1;' LANGUAGE sql;

CREATE FUNCTION priv_testfunc1(int) RETURNS int AS 'select 2 * $1;' LANGUAGE sql;

CREATE FUNCTION sro_ifun(int) RETURNS int AS $$
BEGIN
	ASSERT current_user <> 'postgres',
		format('CURRENT_USER ASSERTION FAILURE! sro_ifun(%s) called by %s', $1, current_user);
	RETURN $1;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE FUNCTION priv_testfunc2(int) RETURNS int AS 'select 3 * $1;' LANGUAGE sql;

CREATE FUNCTION mv_action() RETURNS bool LANGUAGE sql AS
	'DECLARE c CURSOR WITH HOLD FOR SELECT public.unwanted_grant(); SELECT true';

CREATE OR REPLACE FUNCTION mv_action() RETURNS bool LANGUAGE sql AS
	'INSERT INTO public.sro_trojan_table DEFAULT VALUES; SELECT true';

CREATE FUNCTION sro_trojan() RETURNS trigger LANGUAGE plpgsql AS
	'BEGIN PERFORM public.unwanted_grant(); RETURN NULL; END';

CREATE FUNCTION testns.priv_testfunc(int) RETURNS int AS 'select 3 * $1;' LANGUAGE sql;

CREATE FUNCTION priv_testfunc5a(a priv_testdomain1) RETURNS int LANGUAGE SQL AS $$ SELECT $1 $$;

CREATE OR REPLACE FUNCTION unwanted_grant() RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    ASSERT current_user <> 'postgres', 
        format('CURRENT_USER ASSERTION FAILURE! unwanted_grant() called by %s', current_user);
END;
$$;

CREATE FUNCTION ifun(int8) RETURNS int8 AS $$
BEGIN
	ASSERT current_user <> 'postgres',
		format('CURRENT_USER ASSERTION FAILURE! ifun(%s) called by %s', $1, current_user);
	RETURN $1;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE FUNCTION priv_testfunc6a(b int) RETURNS priv_testdomain1 LANGUAGE SQL AS $$ SELECT $1::priv_testdomain1 $$;

CREATE OPERATOR !+! (PROCEDURE = int4pl, LEFTARG = priv_testdomain1, RIGHTARG = priv_testdomain1);

CREATE TABLE test5a (a int, b priv_testdomain1);

CREATE FUNCTION unwanted_grant_nofail(int) RETURNS int
        IMMUTABLE LANGUAGE plpgsql AS $$
BEGIN
        PERFORM public.unwanted_grant();
        RAISE WARNING 'owned';
        RETURN 1;
EXCEPTION WHEN OTHERS THEN
        RETURN 2;
END$$;

CREATE MATERIALIZED VIEW sro_index_mv AS SELECT 1 AS c;

CREATE UNIQUE INDEX ON sro_index_mv (c) WHERE unwanted_grant_nofail(1) > 0;

CREATE USER user1;      

SET SESSION AUTHORIZATION user1;