import sys
sys.modules["pybeacon.dialects.dameng"] = sys.modules[__name__]

import _import_hook
import os, re
from pathlib import Path
from typing import Iterator, List, Dict
from langchain_community.document_loaders import DirectoryLoader, CSVLoader
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from pybeacon import PYBEACON_ROOT_DIR
import subprocess, time
from pybeacon.clients.basic.basic_client import BasicClient
from pybeacon.clients.universe.creator_wrapper import create_clients
from pybeacon.clients.universe.custom_ini_client import CustomIniClient
from pybeacon.clients.universe.multiple_process_client import (
    TimeoutMultiprocessingClient,
)
from pybeacon.clients.universe.user_switch_client import UserSwitchClient
from pybeacon.dialects.dialect import Dialect
from pybeacon.generation.corpus import Corpus
from pybeacon.generation.corpus_parser.base_parser import SimpleParser
from pybeacon.generation.corpus_parser.file_parser import MarkdownCodeParser
from pybeacon.generation.grant_stmt.dbms.dameng import DMGeneratorSingle
from pybeacon.beacon.metadata import StatementEx
from pybeacon.logging.configure import get_console_logger
from pybeacon.dialects.constants import get_dameng_system_tables
from tests.generation.test_corpus_constructor import UserClientConfig

console_logger = get_console_logger(__package__ + "." + os.path.basename(__file__))


class Dameng(Dialect):
    class DocumentLoader(Dialect.DocumentLoader):
        def lazy_load(self) -> Iterator[Document]:
            loader = CSVLoader(
                file_path=Dameng.DOC_FILE_PATH,
                source_column="title",
                content_columns="text",
            )
            return loader.lazy_load()

    class CorpusLoader(Dialect.CorpusLoader):
        def lazy_load(self) -> Iterator[Corpus]:
            loader = CSVLoader(
                file_path=Dameng.LLM_DOC2CORPUS_FILE_PATH,
                source_column="title",
                content_columns="text",
            )
            for document in loader.lazy_load():
                name = document.metadata["source"]
                name = re.sub("[\\u4e00-\\u9fff]+", "", name)
                content = document.page_content
                content = re.sub("[\\u4e00-\\u9fff]+", "", content)
                sql_blocks: list[str] = MarkdownCodeParser(content).parse()
                stmts = []
                for sql_block in sql_blocks:
                    cur_stmts = sql_block.split(";")
                    for stmt in cur_stmts:
                        stmt = stmt.strip()
                        if stmt:
                            stmts.append(StatementEx(stmt))
                yield Corpus(name, stmts)

    class Connection:
        def prepare_database(
            self,
            root_user_conf: UserClientConfig | None = None,
            empty_user_conf: UserClientConfig | None = None,
        ) -> tuple[UserSwitchClient, UserClientConfig, UserClientConfig]:
            client = create_clients(
                [TimeoutMultiprocessingClient, UserSwitchClient, CustomIniClient],
                stop_previous_when_switch=False,
                stop_current_after_execution=False,
                reconnect_when_switch=False,
                **empty_user_conf.__dict__,
            )
            client.execute_v2(
                f"DROP USER {empty_user_conf.username} CASCADE",
                **root_user_conf.__dict__,
            )
            client.execute_v2(
                f"CREATE USER {empty_user_conf.username} IDENTIFIED BY {empty_user_conf.password}",
                **root_user_conf.__dict__,
            ).assert_succ()
            client.execute_v2("SELECT 0").assert_succ()
            return client, root_user_conf, empty_user_conf

    class DatabaseCleaner(Dialect.DatabaseCleaner):
        def clean(
            self,
            root_client: BasicClient,
            user_name_to_drop: str,
            database_name_to_drop: str,
            **kwargs,
        ):
            root_client.execute_v2(f"DROP USER {user_name_to_drop} CASCADE", **kwargs)
            root_client.execute_v2(
                f"DROP SCHEMA {database_name_to_drop} CASCADE", **kwargs
            )
            root_client.execute_v2(
                f"DROP USER {database_name_to_drop} CASCADE", **kwargs
            )

        def clean_all(self, root_client: BasicClient, **kwargs):
            client = root_client
            ret = client.execute_v2("SELECT username FROM sys.dba_users", **kwargs)
            ret.assert_succ()
            existing_users = ret.get_result()
            existing_users = [user[0] for user in existing_users]
            console_logger.debug(
                f"Drop existing users...", existing_users=existing_users
            )
            system_users = {"SYSDBA", "SYSAUDITOR", "SYSSSO", "SYS"}
            for user in existing_users:
                if user not in system_users:
                    try:
                        client.execute_v2(
                            f"DROP USER {user} CASCADE", **kwargs
                        ).assert_succ()
                    except Exception as e:
                        console_logger.warning(f"Failed to drop user {user}: {str(e)}")
            existing_schemas = client.execute_v2(
                "SELECT name FROM sys.sysobjects WHERE type$='SCH'", **kwargs
            ).get_result()
            existing_schemas = [schema[0] for schema in existing_schemas]
            console_logger.debug(
                f"Check remaining schemas...", existing_schemas=existing_schemas
            )
            system_schemas = {"SYSDBA", "SYSAUDITOR", "SYSSSO", "SYS", "CTISYS", "DMHR"}
            for schema in existing_schemas:
                if schema not in system_schemas:
                    try:
                        client.execute_v2(
                            f"DROP SCHEMA {schema} CASCADE", **kwargs
                        ).assert_succ()
                    except Exception as e:
                        console_logger.warning(
                            f"Failed to drop schema {schema}: {str(e)}"
                        )

        def init_from_empty(
            self,
            root_client: BasicClient,
            user_name_to_create: str,
            database_name_to_create: str,
            password: str = "12345678910",
            **kwargs,
        ):
            password_clause = f"IDENTIFIED BY {password}"
            root_client.execute_v2(
                f"CREATE USER {user_name_to_create} {password_clause}", **kwargs
            ).assert_succ()
            root_client.execute_v2(
                f"CREATE SCHEMA {database_name_to_create}", **kwargs
            ).assert_succ()
            root_client.execute_v2(
                f"CREATE TABLE {database_name_to_create}.w (a INT)", **kwargs
            ).assert_succ()
            root_client.execute_v2(
                f"GRANT SELECT ON {database_name_to_create}.w TO {user_name_to_create}",
                **kwargs,
            ).assert_succ()

        def reset(
            self,
            root_client: BasicClient,
            user_name_to_reset: str,
            database_name_to_reset: str,
            password: str = "12345678910",
            **kwargs,
        ):
            try:
                self.clean(
                    root_client, user_name_to_reset, database_name_to_reset, **kwargs
                )
            except:
                pass
            self.init_from_empty(
                root_client,
                user_name_to_reset,
                database_name_to_reset,
                password,
                **kwargs,
            )

        def reset_all(
            self,
            root_client: BasicClient,
            user_name_to_reset: str,
            database_name_to_reset: str,
            password: str = "12345678910",
            **kwargs,
        ):
            self.clean_all(root_client, **kwargs)
            self.init_from_empty(
                root_client,
                user_name_to_reset,
                database_name_to_reset,
                password,
                **kwargs,
            )

    class MetaQuery(Dialect.MetaQuery):
        def get_metaqueries(self, schema: str | None = None) -> list[str]:
            queries = [
                f"""
                SELECT OBJECT_NAME AS name, OBJECT_TYPE AS type, OWNER AS parentname FROM SYS.ALL_OBJECTS 
                WHERE OBJECT_TYPE in ('TABLE', 'VIEW', 'SEQUENCE', 'FUNCTION', 'PROCEDURE', 'SYNONYM', 'INDEX', 'CONSTRAINT') 
                {"AND OWNER = "+f"'{schema}'"if schema else""}
                """,
                f"""
                SELECT COLUMN_NAME AS name, 'COLUMN' AS type, TABLE_NAME AS parentname FROM SYS.ALL_TAB_COLUMNS 
                {"WHERE OWNER = "+f"'{schema}'"if schema else""}
                """,
                f"""
                SELECT TRIGGER_NAME AS name, 'TRIGGER' AS type, TABLE_NAME AS parentname 
                FROM SYS.ALL_TRIGGERS 
                {"WHERE OWNER = "+f"'{schema}'"if schema else""}
                """,
                "SELECT USERNAME AS name, 'USER' AS type, NULL AS parentname FROM SYS.ALL_USERS",
                f"SELECT OBJECT_NAME AS name, 'SCHEMA' AS type, NULL AS parentname FROM SYS.ALL_OBJECTS\n                WHERE OBJECT_TYPE = 'SCH'",
                f"""SELECT OBJECT_NAME AS name, 'OTHERS' AS type, OWNER AS parentname FROM SYS.ALL_OBJECTS
                WHERE OBJECT_TYPE NOT IN ('TABLE', 'VIEW', 'SEQUENCE', 'FUNCTION', 'PROCEDURE', 'SYNONYM', 'INDEX', 'CONSTRAINT', 'SCH')
                {"AND OWNER = "+f"'{schema}'"if schema else""}
                """,
            ]
            return queries

        def get_systable_names_query(self, version=0) -> str:
            return "SELECT concat(owner, '.', table_name) FROM all_tables UNION ALL SELECT concat(owner, '.', view_name) FROM sys.all_views"

        def get_systable_names(self) -> list[str]:
            return get_dameng_system_tables()

    class GrantGenerator(DMGeneratorSingle):
        pass

    INITIAL_SAMPLE_STATEMENT = [
        "CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) )",
        "CREATE TABLE tbl2 ( my_2_col VARCHAR(255) )",
        "CREATE INDEX my_index ON tbl1 (my_1_col)",
        "CREATE OR REPLACE TRIGGER my_trigger BEFORE INSERT ON tbl1 FOR EACH ROW \n            BEGIN \n            :NEW.my_2_col := NULL;\n            END;",
        "CREATE OR REPLACE FUNCTION my_function(a INT, b INT) RETURN INT AS\nBEGIN\n  RETURN a + b;\nEND;",
        "CREATE VIEW my_view AS SELECT my_1_col FROM tbl1",
        "CREATE INDEX my_index ON tbl2 (my_2_col)",
        "INSERT INTO tbl1 VALUES (1, 'a')",
        "SELECT * FROM tbl1",
        "SELECT * FROM tbl2",
        "CREATE SEQUENCE my_sequence INCREMENT BY 1000 START WITH 5 NOMAXVALUE NOMINVALUE CACHE 10;",
        "CREATE SYNONYM symonym_tbl1 FOR tbl1",
    ]
    INITIAL_SAMPLE_STATEMENT_METADATA = [
        ("my_1_col", "COLUMN", ""),
        ("my_2_col", "COLUMN", ""),
        ("tbl1", "TABLE", ""),
        ("tbl2", "TABLE", ""),
        ("my_index", "INDEX", "tbl1"),
        ("my_trigger", "TRIGGER", ""),
        ("my_function", "FUNCTION", ""),
        ("my_view", "VIEW", ""),
        ("my_sequence", "SEQUENCE", ""),
        ("symonym_tbl1", "SYNONYM", ""),
    ]
    DSN_NAME = "dameng"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="dameng", username="SYSDBA", password="SYSDBA001", database="SYSDBA"
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="dameng", username="SYSDBA", password="SYSDBA001", database="TESTDB"
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="dameng", username="FOO", password="12345678910", database="TESTDB"
    )
    SQLGLOT_DIALECT = "oracle"

    @classmethod
    def reset_default_database_instance(
        cls,
        port_number: int = 30236,
        image_version: str = "dm8_20241022_rev244896_x86_rh6_64",
        container_name: str = "some-dameng",
    ) -> None:
        subprocess.run(["docker", "container", "rm", "-f", container_name], check=False)
        time.sleep(5)
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "-p",
                f"{port_number}:5236",
                "--restart=always",
                f"--name={container_name}",
                "--privileged=true",
                "-e",
                "LD_LIBRARY_PATH=/opt/dmdbms/bin",
                "-e",
                "PAGE_SIZE=16",
                "-e",
                "EXTENT_SIZE=32",
                "-e",
                "LOG_SIZE=1024",
                "-e",
                "UNICODE_FLAG=1",
                "-e",
                "INSTANCE_NAME=dm8_test",
                f"greyhawk/dm8_single:{image_version}",
            ],
            check=True,
        )
        port_override = dict(port=port_number)
        init_config = {**cls.DEFAULT_INIT_CONFIG, **port_override}
        cls.wait_for_database_ready(
            config=init_config, max_wait_seconds=90, check_interval_seconds=3.0
        )
        cls._init_database_with_cleaner(
            init_config=port_override, test_config=port_override
        )

    class HealthChecker(Dialect.HealthChecker):
        @classmethod
        def connection_testing_sql(cls) -> str:
            return "SELECT 1 FROM dual"

    class DockerOperation(Dialect.DockerOperation):
        DOCKER_PORT_NUMBER = 30236
        DOCKER_IMAGE_VERSION = "dm8_20241022_rev244896_x86_rh6_64"
        DOCKER_CONTAINER_NAME = "some-dameng"

        def __init__(self, dbms_cls=None):
            super().__init__(dbms_cls or Dameng)
