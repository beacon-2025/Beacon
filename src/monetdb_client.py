import sys
sys.modules["pybeacon.dialects.monetdb"] = sys.modules[__name__]

import _import_hook
import logging, os
from pathlib import Path
from pprint import pprint
from time import sleep
from typing import Iterator, List, Dict
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from tqdm import tqdm
from pybeacon import PYBEACON_ROOT_DIR
import subprocess, time
from pybeacon.clients.native.monetdb_client import MonetdbClient

load_dotenv(dotenv_path=Path(PYBEACON_ROOT_DIR) / os.pardir / ".env")
from pybeacon.clients.basic.basic_client import BasicClient
from pybeacon.dialects.dialect import Dialect
from pybeacon.generation.corpus import Corpus
from pybeacon.generation.corpus_parser.base_parser import SimpleParser
from pybeacon.generation.grant_stmt.dbms.clickhouse import ClickHouseGeneratorSingle
from pybeacon.generation.grant_stmt.dbms.monetdb import MonetDBGeneratorNormal
from pybeacon.beacon.metadata import StatementEx
from pybeacon.logging.configure import get_console_logger
from pybeacon.dialects.constants import get_monetdb_system_tables

console_logger = get_console_logger(logger_name=__name__)
console_logger._logger.setLevel(logging.DEBUG)


class MonetDB(Dialect):
    OBJECT_TYPES: list[str] = [
        "SCHEMA",
        "TABLE",
        "VIEW",
        "SEQUENCE",
        "FUNCTION",
        "PROCEDURE",
        "AGGREGATE",
        "LOADER",
        "TRIGGER",
        "TYPE",
        "INDEX",
        "COLUMN",
        "CONSTRAINT",
        "PARAMETER",
        "FILTER FUNCTION",
        "WINDOW FUNCTION",
        "MERGE TABLE",
        "REMOTE TABLE",
        "REPLICA TABLE",
        "UNLOGGED TABLE",
        "TEMPORARY TABLE",
        "IMPRINTS INDEX",
        "ORDERED INDEX",
        "AGGREGATE EXTERNAL",
        "AGGREGATE LANGUAGE",
        "FUNCTION EXTERNAL",
        "FUNCTION LANGUAGE",
        "PROCEDURE EXTERNAL",
        "WINDOW EXTERNAL",
        "TYPE EXTERNAL",
        "USER",
        "ROLE",
    ]
    DEFAULT_PASSWORD = "monetdb"

    class CorpusLoader(Dialect.CorpusLoader):
        def lazy_load(self) -> Iterator[Corpus]:
            raise NotImplementedError(
                "MonetDB does not support lazy loading of corpus."
            )

    class CorpusParser(Dialect.CorpusParser):
        def __init__(self):
            super().__init__("/dev/null")
            raise NotImplementedError(
                "MonetDB does not support lazy loading of corpus."
            )

    class DatabaseCleaner(Dialect.DatabaseCleaner):
        def clean(
            self,
            root_client: BasicClient,
            user_name_to_drop: str,
            schema_name_to_drop: str,
            **kwargs,
        ):
            root_client.execute_v2(
                f"ALTER USER {user_name_to_drop} SET SCHEMA sys", **kwargs
            )
            root_client.execute_v2(f"DROP SCHEMA {user_name_to_drop} CASCADE", **kwargs)
            root_client.execute_v2(f"DROP USER {user_name_to_drop}", **kwargs)
            root_client.execute_v2(
                f"DROP SCHEMA {schema_name_to_drop} CASCADE", **kwargs
            )

        def clean_all(self, root_client: BasicClient, **kwargs):
            ret = root_client.execute_v2("SELECT name FROM sys.users", **kwargs)
            ret.assert_succ()
            users = ret.get_result()
            for (user,) in users:
                if user != "monetdb":
                    root_client.execute_v2(
                        f"ALTER USER {user} SET SCHEMA sys", **kwargs
                    )
                    root_client.execute_v2(f"DROP SCHEMA {user}", **kwargs)
                    root_client.execute_v2(f"DROP USER {user}", **kwargs)
            schemas = root_client.execute_v2(
                "SELECT name FROM sys.schemas WHERE system = false", **kwargs
            ).get_result()
            for (schema,) in schemas:
                root_client.execute_v2(f"DROP SCHEMA {schema} CASCADE", **kwargs)

        def init_from_empty(
            self,
            root_client: BasicClient,
            user_name_to_create: str,
            schema_name_to_create: str,
            **kwargs,
        ):
            root_client.execute_v2(
                f"CREATE SCHEMA {schema_name_to_create}", **kwargs
            ).assert_succ()
            root_client.execute_v2(
                f"CREATE USER {user_name_to_create} WITH PASSWORD '{MonetDB.DEFAULT_PASSWORD}' NAME '{user_name_to_create}'",
                **kwargs,
            ).assert_succ()
            root_client.execute_v2(
                f"SET SCHEMA {schema_name_to_create}", **kwargs
            ).assert_succ()

        def reset(
            self,
            root_client: BasicClient,
            user_name_to_reset: str,
            schema_name_to_reset: str,
            **kwargs,
        ):
            self.clean(root_client, user_name_to_reset, schema_name_to_reset, **kwargs)
            self.init_from_empty(
                root_client, user_name_to_reset, schema_name_to_reset, **kwargs
            )

        def reset_all(
            self,
            root_client: BasicClient,
            user_name_to_reset: str,
            schema_name_to_reset: str,
            **kwargs,
        ):
            self.clean_all(root_client, **kwargs)
            self.init_from_empty(
                root_client, user_name_to_reset, schema_name_to_reset, **kwargs
            )

    class MetaQuery(Dialect.MetaQuery):
        def get_metaqueries(self, schema: str = None) -> list[str]:
            queries = [
                "SELECT name, 'SCHEMA' AS type, NULL AS parentname FROM sys.schemas",
                f"""SELECT t.name, 'TABLE' AS type, s.name AS parentname FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.id {"WHERE s.name = '"+schema+"'"if schema else""}""",
                f"""SELECT t.name, 'VIEW' AS type, s.name AS parentname FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.id WHERE t.type = (SELECT table_type_id FROM sys.table_types WHERE table_type_name = 'VIEW'){" AND s.name = '"+schema+"'"if schema else""}""",
                f"""SELECT c.name, 'COLUMN' AS type, tbl.name AS parentname FROM sys.columns c JOIN sys.tables tbl ON c.table_id = tbl.id {"WHERE tbl.schema_id = (SELECT id FROM sys.schemas WHERE name = '"+schema+"')"if schema else""}""",
                "SELECT name, 'USER' AS type, NULL AS parentname FROM sys.users",
                "SELECT name, 'ROLE' AS type, NULL AS parentname FROM sys.roles",
                "SELECT u.name || ' -> ' || r.name AS name, 'USER_ROLE' AS type, NULL AS parentname FROM sys.user_role ur JOIN sys.auths u ON ur.login_id = u.id JOIN sys.roles r ON ur.role_id = r.id",
            ]
            return queries

        def get_systable_names_query(self, version=0) -> str:
            return "SELECT s.name || '.' || t.name FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.id WHERE s.system = true;"

        def get_systable_names(self) -> list[str]:
            return get_monetdb_system_tables()

    class GrantGenerator(MonetDBGeneratorNormal):
        pass

    INITIAL_SAMPLE_STATEMENT = [
        "CREATE SCHEMA IF NOT EXISTS example_schema;",
        "CREATE TABLE IF NOT EXISTS example_table (example_id INT, example_name VARCHAR(100));",
        "INSERT INTO example_table VALUES (1, 'Alice'), (2, 'Bob');",
        "CREATE VIEW example_view AS SELECT example_id, example_name FROM example_table;",
    ]
    INITIAL_SAMPLE_STATEMENT_METADATA = [
        ("example_schema", "SCHEMA", ""),
        ("example_table", "TABLE", ""),
        ("example_id", "COLUMN", "example_table"),
        ("example_name", "COLUMN", "example_table"),
        ("example_view", "VIEW", ""),
    ]
    DSN_NAME = "monetdb"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="monetdb_dialect",
        username="monetdb",
        password="monetdb",
        database="sys",
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="monetdb_dialect",
        username="monetdb",
        password="monetdb",
        database="test",
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="monetdb_dialect",
        username="foo",
        password=DEFAULT_PASSWORD,
        database="test",
    )
    SQLGLOT_DIALECT = "mysql"

    @classmethod
    def reset_default_database_instance(
        cls,
        port_number: int = 50000,
        image_version: str = "Mar2025-SP1",
        container_name: str = "some-monetdb",
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
                "-e",
                "MDB_DB_ADMIN_PASS=monetdb",
                "-p",
                f"{port_number}:50000",
                f"monetdb/monetdb:{image_version}",
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

    class DockerOperation(Dialect.DockerOperation):
        DOCKER_PORT_NUMBER = 50000
        DOCKER_IMAGE_VERSION = "Mar2025-SP1"
        DOCKER_CONTAINER_NAME = "some-monetdb"

        def __init__(self, dbms_cls=None):
            super().__init__(dbms_cls or MonetDB)


if __name__ == "__main__":
    root_client = MonetdbClient(
        host="localhost",
        port=50000,
        username="monetdb",
        password="monetdb",
        database="monetdb",
        schema="sys",
    )
    blacklist = [
        "SELECT MIN(column1) FROM (SELECT column1 FROM table1 UNION SELECT column1 FROM table2);",
        "MERGE INTO table1 T USING (SELECT column1, column2 FROM (SELECT column1, column2 FROM table2 UNION SELECT column1, column2 FROM view1)) AS S ON T.column1 = S.column1 WHEN MATCHED THEN UPDATE SET T.column2 = S.column2;",
        "CREATE TRIGGER trigger_truncate_conditional AFTER TRUNCATE ON table1 FOR EACH STATEMENT WHEN (EXISTS (SELECT 1 FROM table2)) CALL procedure2();",
        "COPY SELECT * FROM table1 INTO BINARY '/path/to/table1_data.bin';",
        "CREATE TRIGGER trigger6 AFTER UPDATE ON table1 REFERENCING OLD TABLE AS old_table NEW TABLE AS new_table FOR EACH STATEMENT SELECT * FROM sys.triggers;",
        "CREATE TRIGGER trigger10 AFTER DELETE ON table2 REFERENCING OLD ROW AS old_row FOR EACH STATEMENT SELECT * FROM sys.triggers WHERE name = 'trigger10';",
        "CREATE REMOTE TABLE remote_table1 (column1 INT, column2 VARCHAR(100)) ON 'mapi:monetdb://localhost:50000/dbname';",
        "DROP TABLE IF EXISTS table1 CASCADE;",
        "COMMENT ON FUNCTION function1 IS 'This function calculates the total sales for a given year.';",
        "COPY SELECT * FROM table1 LIMIT 10 INTO BINARY '/path/to/table1_top10.bin';",
        "COPY SELECT * FROM table1 INTO BINARY 'table1_data.bin' ON CLIENT;",
        "COPY SELECT column1, column2 FROM table1 LIMIT 10 INTO BINARY 'limited_data.bin' ON CLIENT;",
        "COPY SELECT column1, column2 FROM table2 INTO BINARY '/path/to/table2_columns.bin';",
        "COPY",
        "CREATE TRIGGER trigger3 AFTER DELETE ON table1 FOR EACH STATEMENT WHEN (EXISTS (SELECT 1 FROM table1 WHERE column1 = 5)) SELECT column1 INTO variable3 FROM table1 WHERE column2 = 'value';",
    ]
    a = MonetDB()
    istart = 1500

    def accept_item(i: int) -> bool:
        return 0 <= i < 500 or 1000 <= i <= 1500 or 2000 < i < 2700

    pbar = tqdm(list(enumerate(a.LLM_CORPUS_WITH_METADATA.data[:])))
    for i, item in pbar:
        pbar.refresh()
        if not accept_item(i):
            continue
        stmt_with_metadata_list = item.list_of_stmt_and_metadata
        for stmt_with_metadata in stmt_with_metadata_list:
            stmt = stmt_with_metadata.stmt
            add = stmt_with_metadata.add
            use = stmt_with_metadata.use
            delete = stmt_with_metadata.delete
            if any(black in stmt for black in blacklist):
                continue
            if True:
                pass
                ret = root_client.execute_v2(stmt)
                if ret.is_succ():
                    pass
                else:
                    pass
                ret = root_client.execute_v2(
                    MonetDB.HealthChecker.connection_testing_sql()
                )
                if ret.is_fail():
                    print("[STMT]", stmt)
                    print("I am going to reconnect...", flush=True)
                    sleep(3)
                    root_client = MonetdbClient(
                        host="localhost",
                        port=50000,
                        username="monetdb",
                        password="monetdb",
                        database="monetdb",
                        schema="sys",
                    )
                    print("Reconnection is done", flush=True)
    print("All statements executed successfully.")
    exit(0)
