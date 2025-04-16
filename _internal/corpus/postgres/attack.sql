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

CREATE FUNCTION sro_ifun(int) RETURNS int AS $$
BEGIN
	ASSERT current_user <> 'postgres',
		format('CURRENT_USER ASSERTION FAILURE! sro_ifun(%s) called by %s', $1, current_user);
	RETURN $1;
END;
$$ LANGUAGE plpgsql IMMUTABLE;