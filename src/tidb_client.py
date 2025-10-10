import sys
sys.modules["pybeacon.dialects.tidb"] = sys.modules[__name__]

import _import_hook
from pathlib import Path
from typing import Iterator, List, Dict
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from pydantic import BaseModel, Field
from pybeacon import PYBEACON_ROOT_DIR
import subprocess, time
from pybeacon.dialects.dialect import Dialect
from pybeacon.dialects.mysql import MySQL
from pybeacon.generation.corpus import Corpus
from pybeacon.beacon.metadata import StatementEx
from pybeacon.logging.configure import get_console_logger
from pybeacon.dialects.constants import get_tidb_system_tables

console_logger = get_console_logger(logger_name=__name__)


class TiDB(MySQL):
    class CorpusLoaderOfficial(Dialect.CorpusLoader):
        def lazy_load(self) -> Iterator[Corpus]:
            loader = DirectoryLoader(
                path=str(TiDB.CORPUS_PATH), glob="**/*.test", loader_cls=TextLoader
            )
            for document in loader.lazy_load():
                name = document.metadata["source"]
                name = Path(name).name
                content = document.page_content
                stmts = content.split(";")
                stmtex_list = [StatementEx(stmt) for stmt in stmts]
                yield Corpus(name=name, stmtex_list=stmtex_list)

    class MetaQuery(MySQL.MetaQuery):
        def get_systable_names_query(self, version=0) -> str:
            return "SELECT concat(table_schema, '.', table_name) FROM information_schema.tables\n            WHERE table_name NOT IN ('tidb_mdl_view', 'tidb_profile_cpu', 'inspection_result')"

        def get_systable_names(self) -> list[str]:
            return get_tidb_system_tables()

    DSN_NAME = "tidb"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="tidb", username="root", password="", database="mysql"
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="tidb", username="root", password="", database="test"
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="tidb", username="foooo", password="", database="test"
    )

    @classmethod
    def reset_default_database_instance(
        cls,
        port_number: int = 4000,
        image_version: str = "v8.5.2",
        container_name: str = "some-tidb-0",
    ) -> None:
        subprocess.run(["docker", "container", "rm", "-f", container_name], check=False)
        time.sleep(5)
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-p",
                f"{port_number}:4000",
                "--log-opt",
                "max-size=10m",
                "--log-opt",
                "max-file=3",
                "--log-driver",
                "json-file",
                f"pingcap/tidb:{image_version}",
            ],
            check=True,
        )
        port_override = dict(port=port_number)
        init_config = {**cls.DEFAULT_INIT_CONFIG, **port_override}
        cls.wait_for_database_ready(
            config=init_config, max_wait_seconds=40, check_interval_seconds=2.0
        )
        cls._init_database_with_cleaner(
            init_config=port_override, test_config=port_override
        )

    class DockerOperation(MySQL.DockerOperation):
        DOCKER_PORT_NUMBER = 4000
        DOCKER_IMAGE_VERSION = "v8.5.2"
        DOCKER_CONTAINER_NAME = "some-tidb"

        def __init__(self, dbms_cls=None):
            super().__init__(dbms_cls or TiDB)

    INITIAL_SAMPLE_STATEMENT = tidb_statements = [
        "CREATE DATABASE IF NOT EXISTS db1;",
        "CREATE DATABASE IF NOT EXISTS db2;",
        "SHOW DATABASES;",
        "SHOW SCHEMAS;",
        "USE db1;",
        "ALTER DATABASE db1 CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;",
        "SHOW CREATE DATABASE db1;",
        "CREATE PLACEMENT POLICY policy1 PRIMARY_REGION='us-east-1' REGIONS='us-east-1,us-west-1';",
        "ALTER PLACEMENT POLICY policy1 PRIMARY_REGION='us-west-1';",
        "SHOW CREATE PLACEMENT POLICY policy1;",
        "ALTER RANGE global PLACEMENT POLICY policy1;",
        "SHOW PLACEMENT;",
        "SHOW PLACEMENT FOR db1.table1;",
        "SHOW PLACEMENT LABELS;",
        "DROP PLACEMENT POLICY IF EXISTS policy1;",
        "CREATE RESOURCE GROUP rg1 RU_PER_SEC = 1000 BURSTABLE;",
        "ALTER RESOURCE GROUP rg1 RU_PER_SEC = 2000;",
        "SHOW CREATE RESOURCE GROUP rg1;",
        "SET RESOURCE GROUP rg1;",
        "DROP RESOURCE GROUP rg1;",
        "CREATE USER IF NOT EXISTS 'user1'@'%' IDENTIFIED BY 'pwd1';",
        "CREATE USER IF NOT EXISTS 'user2'@'%' IDENTIFIED BY 'pwd2';",
        "CREATE ROLE IF NOT EXISTS 'role1';",
        "CREATE ROLE IF NOT EXISTS 'role2';",
        "GRANT ALL PRIVILEGES ON db1.* TO 'user1'@'%';",
        "GRANT SELECT, INSERT ON db1.table1 TO 'user2'@'%';",
        "GRANT 'role1' TO 'user1'@'%';",
        "GRANT 'role2' TO 'user2'@'%';",
        "SET ROLE 'role1';",
        "SET DEFAULT ROLE 'role1' TO 'user1'@'%';",
        "ALTER USER 'user1'@'%' IDENTIFIED BY 'pwd1_new';",
        "SET PASSWORD FOR 'user2'@'%' = 'pwd2_new';",
        "SHOW GRANTS FOR 'user1'@'%';",
        "SHOW CREATE USER 'user1'@'%';",
        "SHOW PRIVILEGES;",
        "REVOKE SELECT, INSERT ON db1.table1 FROM 'user2'@'%';",
        "REVOKE 'role2' FROM 'user2'@'%';",
        "RENAME USER 'user2'@'%' TO 'user2_renamed'@'%';",
        "FLUSH PRIVILEGES;",
        "DROP ROLE 'role2';",
        "DROP USER 'user2_renamed'@'%';",
        "CREATE TABLE table1 (id BIGINT PRIMARY KEY, c1 INT, c2 VARCHAR(100));",
        "CREATE TABLE table2 LIKE table1;",
        "CREATE TABLE table_partitioned (id INT, c1 INT, KEY k1(c1)) PARTITION BY RANGE (id) (PARTITION p0 VALUES LESS THAN (100), PARTITION p1 VALUES LESS THAN (MAXVALUE));",
        "SHOW TABLES;",
        "SHOW TABLE STATUS LIKE 'table1';",
        "DESC table1;",
        "DESCRIBE table1;",
        "SHOW COLUMNS FROM table1;",
        "SHOW FIELDS FROM table1;",
        "SHOW CREATE TABLE table1;",
        "CREATE INDEX idx_table1_c1 ON table1(c1);",
        "SHOW INDEXES FROM table1;",
        "ALTER TABLE table1 ADD COLUMN c3 DECIMAL(10,2) DEFAULT 0;",
        "ALTER TABLE table1 MODIFY COLUMN c2 VARCHAR(200);",
        "ALTER TABLE table1 CHANGE COLUMN c3 c3_renamed DECIMAL(12,2);",
        "ALTER TABLE table1 RENAME COLUMN c1 TO c1_renamed;",
        "ALTER TABLE table1 RENAME TO table1_renamed;",
        "ALTER TABLE table1_renamed ADD INDEX idx_table1_c1_renamed(c1_renamed);",
        "ALTER TABLE table1_renamed RENAME INDEX idx_table1_c1_renamed TO idx_table1_c1_new;",
        "ALTER TABLE table1_renamed ALTER INDEX idx_table1_c1_new INVISIBLE;",
        "TRUNCATE TABLE table2;",
        "DROP TABLE IF EXISTS table2;",
        "CREATE VIEW view1 AS SELECT id, c1_renamed FROM table1_renamed WHERE c1_renamed > 0;",
        "SHOW CREATE TABLE view1;",
        "DROP VIEW view1;",
        "CREATE SEQUENCE sequence1 START WITH 1 INCREMENT BY 1 MINVALUE 1 MAXVALUE 100 NOCYCLE;",
        "ALTER SEQUENCE sequence1 INCREMENT BY 2 MAXVALUE 1000;",
        "SHOW CREATE SEQUENCE sequence1;",
        "SELECT NEXT VALUE FOR sequence1;",
        "DROP SEQUENCE sequence1;",
        "CREATE TABLE table_dist (a INT, b INT, KEY idx_b(b)) PARTITION BY RANGE (a) (PARTITION p1 VALUES LESS THAN (10000), PARTITION p2 VALUES LESS THAN (MAXVALUE));",
        "DISTRIBUTE TABLE table_dist;",
        "SHOW TABLE table_dist DISTRIBUTIONS;",
        "SHOW DISTRIBUTION JOBS;",
        "CANCEL DISTRIBUTION JOB 1;",
        "SPLIT REGION FOR TABLE table_dist BETWEEN (0) AND (100000) REGIONS 2;",
        "SHOW TABLE REGIONS table_dist;",
        "SHOW TABLE NEXT_ROW_ID db1.table1_renamed;",
        "SHOW TABLE STATUS FROM db1;",
        "ANALYZE TABLE table1_renamed;",
        "SHOW ANALYZE STATUS;",
        "CREATE BINDING FOR SELECT * FROM table1_renamed WHERE c1_renamed = 1 USING SELECT * FROM table1_renamed USE INDEX(idx_table1_c1_new) WHERE c1_renamed = 1;",
        "SHOW BINDINGS;",
        "DROP BINDING FOR SELECT * FROM table1_renamed WHERE c1_renamed = 1;",
        "LOAD STATS 's3://bucket/statistics.json';",
        "SHOW COLUMN_STATS_USAGE;",
        "SHOW STATS_META;",
        "SHOW STATS_HEALTHY;",
        "SHOW STATS_BUCKETS WHERE table_name = 'table1_renamed';",
        "SHOW STATS_HISTOGRAMS WHERE table_name = 'table1_renamed';",
        "SHOW STATS_TOPN WHERE table_name = 'table1_renamed';",
        "SHOW STATS_LOCKED;",
        "LOCK STATS db1.table1_renamed;",
        "UNLOCK STATS db1.table1_renamed;",
        "DROP STATS db1.table1_renamed;",
        "INSERT INTO table1_renamed (id, c1_renamed, c2) VALUES (1, 10, 'row1');",
        "INSERT INTO table1_renamed (id, c1_renamed, c2) VALUES (2, 20, 'row2'), (3, 30, 'row3');",
        "REPLACE INTO table1_renamed (id, c1_renamed, c2) VALUES (1, 100, 'row1_replace');",
        "UPDATE table1_renamed SET c2 = 'row2_updated' WHERE id = 2;",
        "DELETE FROM table1_renamed WHERE id = 3;",
        "WITH cte AS (SELECT id, c1_renamed FROM table1_renamed) SELECT * FROM cte WHERE c1_renamed > 0;",
        "SELECT id, c1_renamed, c2 FROM table1_renamed WHERE c1_renamed > 0 ORDER BY c1_renamed LIMIT 10;",
        "TABLE table1_renamed;",
        "DO 1 + 1;",
        "BATCH ON db1.table1_renamed.id LIMIT 1 INSERT INTO table1_renamed SELECT id + 1000, c1_renamed, c2 FROM table1_renamed;",
        "PREPARE stmt1 FROM 'SELECT id, c1_renamed FROM table1_renamed WHERE id = ?';",
        "EXECUTE stmt1 USING @id;",
        "DEALLOCATE PREPARE stmt1;",
        "LOAD DATA LOCAL INFILE '/tmp/data.csv' INTO TABLE table1_renamed FIELDS TERMINATED BY ',' ENCLOSED BY '\"' LINES TERMINATED BY '\\n' (id, c1_renamed, c2);",
        "IMPORT INTO table1_renamed (id, c1_renamed, c2) FROM 's3://bucket/data.csv' FORMAT 'CSV';",
        "SHOW IMPORT JOB;",
        "CANCEL IMPORT JOB 1;",
        "BACKUP DATABASE db1 TO 's3://bucket/backup_db1';",
        "SHOW BACKUPS;",
        "RESTORE DATABASE db1 FROM 's3://bucket/backup_db1';",
        "SHOW RESTORES;",
        "FLASHBACK DATABASE db1 TO TIMESTAMP NOW() - INTERVAL 1 HOUR;",
        "FLASHBACK TABLE table1_renamed TO TIMESTAMP NOW() - INTERVAL 1 HOUR;",
        "FLASHBACK CLUSTER TO TIMESTAMP NOW() - INTERVAL 1 HOUR;",
        "RECOVER TABLE table_dropped;",
        "SHOW VARIABLES;",
        "SHOW STATUS;",
        "SHOW ENGINES;",
        "SHOW PLUGINS;",
        "SHOW CONFIG;",
        "FLUSH STATUS;",
        "FLUSH TABLES;",
        "SHOW PROCESSLIST;",
        "SHOW PROFILES;",
        "SHOW WARNINGS;",
        "SHOW ERRORS;",
        "SHOW BUILTINS;",
        "SHOW CHARACTER SET;",
        "SHOW COLLATION;",
        "SHOW MASTER STATUS;",
        "SHOW PLUGINS;",
        "SHOW TABLES FROM db1;",
        "SHOW TABLES LIKE 'table%';",
        "SHOW TABLE DISTRIBUTION db1.table_dist;",
        "SHOW TRAFFIC JOBS;",
        "LOCK TABLES table1_renamed READ;",
        "UNLOCK TABLES;",
        "ADMIN SHOW DDL JOBS;",
        "ADMIN SHOW DDL JOB QUERIES 5;",
        "ADMIN CHECK TABLE table1_renamed;",
        "ADMIN CHECK INDEX table1_renamed idx_table1_c1_new;",
        "ADMIN CHECKSUM TABLE table1_renamed;",
        "ADMIN CLEANUP INDEX table1_renamed idx_table1_c1_new;",
        "ADMIN PAUSE DDL JOBS 1;",
        "ADMIN RESUME DDL JOBS 1;",
        "ADMIN CANCEL DDL JOBS 1;",
        "ADMIN ALTER DDL JOBS 1 RETRY;",
        "ADMIN RECOVER INDEX table1_renamed idx_table1_c1_new;",
        "ADMIN SET BDR ROLE primary;",
        "ADMIN SHOW BDR ROLE;",
        "ADMIN UNSET BDR ROLE;",
        "EXPLAIN SELECT * FROM table1_renamed WHERE c1_renamed = 10;",
        "EXPLAIN ANALYZE SELECT * FROM table1_renamed WHERE c1_renamed = 10;",
        "TRACE FORMAT='row' SELECT * FROM table1_renamed WHERE c1_renamed = 10;",
        "QUERY WATCH 'SELECT * FROM db1.table1_renamed' FOR 60 SECOND;",
        "CALIBRATE RESOURCE;",
        "TRAFFIC REPLAY FROM '/tmp/traffic' USER='u1' PASSWORD='123456' SPEED=2 READ_ONLY=true;",
        "CANCEL TRAFFIC JOBS;",
        "SHOW BINDINGS;",
        "SHOW COLUMN_STATS_USAGE;",
        "SHOW STATS_META;",
        "SHOW STATUS LIKE 'Threads%';",
        "SHOW TABLE NEXT_ROW_ID db1.table1_renamed;",
        "SHOW TABLE REGIONS db1.table_dist;",
        "SHOW VARIABLES LIKE 'tidb%';",
        "KILL 12345;",
        "UPDATE table1_renamed SET c1_renamed = c1_renamed + 1 WHERE id = 1;",
        "TRUNCATE TABLE table1_renamed;",
        "UNLOCK STATS db1.table1_renamed;",
        "DROP VIEW IF EXISTS view1;",
        "DROP TABLE IF EXISTS table_dist;",
        "DROP TABLE IF EXISTS table_partitioned;",
        "DROP DATABASE IF EXISTS db2;",
    ]
    INITIAL_SAMPLE_STATEMENT = [
        "CREATE TABLE tbl1 (col1 INT);",
        "INSERT INTO tbl1 (col1) VALUES (10);",
    ]
    INITIAL_SAMPLE_STATEMENT_METADATA = [
        ("db1", "DATABASE", ""),
        ("db2", "DATABASE", ""),
        ("policy1", "PLACEMENT POLICY", ""),
        ("rg1", "RESOURCE GROUP", ""),
        ("user1", "USER", ""),
        ("user2", "USER", ""),
        ("user2_renamed", "USER", ""),
        ("role1", "ROLE", ""),
        ("role2", "ROLE", ""),
        ("table1", "TABLE", ""),
        ("table2", "TABLE", ""),
        ("table_partitioned", "TABLE", ""),
        ("table_dist", "TABLE", ""),
        ("table1_renamed", "TABLE", ""),
        ("view1", "VIEW", ""),
        ("sequence1", "SEQUENCE", ""),
        ("id", "COLUMN", "table1"),
        ("c1", "COLUMN", "table1"),
        ("c2", "COLUMN", "table1"),
        ("c3", "COLUMN", "table1"),
        ("c3_renamed", "COLUMN", "table1"),
        ("c1_renamed", "COLUMN", "table1"),
        ("id", "COLUMN", "table1_renamed"),
        ("c1_renamed", "COLUMN", "table1_renamed"),
        ("c2", "COLUMN", "table1_renamed"),
        ("c3_renamed", "COLUMN", "table1_renamed"),
        ("id", "COLUMN", "table_partitioned"),
        ("c1", "COLUMN", "table_partitioned"),
        ("a", "COLUMN", "table_dist"),
        ("b", "COLUMN", "table_dist"),
        ("idx_table1_c1", "INDEX", "table1"),
        ("idx_table1_c1_renamed", "INDEX", "table1_renamed"),
        ("idx_table1_c1_new", "INDEX", "table1_renamed"),
        ("k1", "INDEX", "table_partitioned"),
        ("idx_b", "INDEX", "table_dist"),
    ]
    INITIAL_SAMPLE_STATEMENT_METADATA = [("tbl1", "TABLE", "")]


if __name__ == "__main__":
    a = TiDB()
    LLM_CORPUS = a.LLM_CORPUS
    feature_count = sum(
        len(features) for features in LLM_CORPUS.syntax_features_per_doc
    )
    print(f"Total number of syntax features across all documents: {feature_count}")
