-- Login with the root user
CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) );
CREATE VIEW my_view AS SELECT my_1_col FROM tbl1;
REVOKE ALL ON my_view FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM SYS.vsystexts;
/*
LINEID  ID        SEQNO  TXT
------  --------  -----  -------------------------------------------------------------------------------------------------------------------------------------------
1       16778457  0      CREATE OR REPLACE VIEW my_view AS SELECT my_1_col FROM tbl1;
2       16778457  1         SELECT MY_1_COL FROM TBL1
*/