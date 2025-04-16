CREATE TABLE bttest_a(id int8);
INSERT INTO bttest_a SELECT * FROM generate_series(1, 1000);
CREATE INDEX bttest_a_expr_idx ON bttest_a ((ifun(id) + ifun(0)))
	WHERE ifun(id + 10) > ifun(10);