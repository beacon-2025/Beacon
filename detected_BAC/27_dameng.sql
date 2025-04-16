-- Login with the root user
CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) );
REVOKE ALL ON tbl1 FROM regular_user;

-- Login with user 'regular_user'
SELECT * FROM SYS.vsyscolumns;
/*
LINEID  NAME       ID       COLID  TYPE$    LENGTH$  SCALE  NULLABLE$  DEFVAL  INFO1  INFO2
------  ---------  -------  ------  -------  -------  -----  ----------  ------  -----  -----
1       MY_1_COL   1017     0       INT      4        0      Y           NULL    0      0
2       MY_2_COL   1017     1       VARCHAR  255      0      Y           NULL    0      0
*/