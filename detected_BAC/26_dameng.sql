-- Login with the root user
CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) );
REVOKE ALL ON tbl1 FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM SYS.all_tables_dis_info;
/*
LINEID  SCHEMA_NAME  TABLE_NAME            TABLE_TYPE  DIS_TYPE  DIS_COLS
------  -----------  --------------------  ----------  --------  --------
1       SYSDBA       ##HISTOGRAMS_TABLE     NORMAL      LOCAL     NULL
2       SYSDBA       TBL1                   NORMAL      LOCAL     NULL
*/
