import sys
sys.modules["pybeacon.dialects.mysql"] = sys.modules[__name__]

import _import_hook
import logging, os
from pathlib import Path
from typing import Iterator, List, Dict
from langchain_community.document_loaders import DirectoryLoader
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from pybeacon import PYBEACON_ROOT_DIR
from pybeacon.clients.basic.basic_client import BasicClient
from pybeacon.dialects.dialect import Dialect
from pybeacon.dialects.constants import get_mysql_system_tables
from pybeacon.generation.corpus import Corpus
from pybeacon.generation.corpus_parser.base_parser import SimpleParser
from pybeacon.generation.grant_stmt.dbms.mysql import (
    MysqlGeneratorFull,
    MysqlGeneratorNormal,
)
from pybeacon.beacon.metadata import StatementEx
from pybeacon.logging.configure import get_console_logger

console_logger = get_console_logger(logger_name=__name__)
console_logger._logger.setLevel(logging.INFO)
import subprocess, time


class MySQL(Dialect):
    class DocumentLoader(Dialect.DocumentLoader):
        def lazy_load(self) -> Iterator[Document]:
            loader = DirectoryLoader(str(MySQL.DOC_PATH))
            for doc in loader.lazy_load():
                doc.metadata["source"] = Path(doc.metadata["source"]).name
                yield doc

    class CorpusLoader(Dialect.CorpusLoader):
        def lazy_load(self) -> Iterator[Corpus]:
            simple_parser = SimpleParser(str(MySQL.CORPUS_PATH))
            for file in simple_parser.get_relative_file_list():
                stmts = simple_parser.parse_sql_statements(file)
                stmtex_list = [StatementEx(stmt) for stmt in stmts]
                yield Corpus(name=file, stmtex_list=stmtex_list)

    class CorpusParser(Dialect.CorpusParser):
        def __init__(self):
            super().__init__(str(MySQL.CORPUS_PATH))

    class DatabaseCleaner(Dialect.DatabaseCleaner):
        def clean(
            self,
            root_client: BasicClient,
            user_name_to_drop: str,
            database_name_to_drop: str,
            **kwargs,
        ):
            root_client.execute_v2(f"DROP DATABASE {database_name_to_drop}", **kwargs)
            root_client.execute_v2(f"DROP USER {user_name_to_drop}", **kwargs)

        def clean_all(self, root_client: BasicClient, **kwargs):
            client = root_client
            ret = client.execute_v2("SHOW DATABASES", **kwargs)
            ret.assert_succ()
            existing_databases = ret.get_result()
            console_logger.debug(
                f"Drop existing databases...", existing_databases=existing_databases
            )
            for database_name_tuple in existing_databases:
                database_name = database_name_tuple[0]
                if database_name not in {
                    "mysql",
                    "information_schema",
                    "sys",
                    "performance_schema",
                }:
                    client.execute_v2(f"DROP DATABASE {database_name}", **kwargs)
            existing_users = client.execute_v2(
                "SELECT user FROM mysql.user", **kwargs
            ).get_result()
            existing_users = [user[0] for user in existing_users]
            console_logger.debug(
                f"Drop existing users...", existing_users=existing_users
            )
            drop_all_roles_stmt_gen = (
                "SELECT CONCAT('DROP ROLE ', user, ';') FROM mysql.user"
            )
            drop_all_roles_stmts = client.execute_v2(
                drop_all_roles_stmt_gen, **kwargs
            ).get_result()
            drop_all_roles_stmts = [stmt[0] for stmt in drop_all_roles_stmts]
            dropping_all_users_stmt_gen = "SELECT CONCAT('DROP USER ''', user, '''@''', host, ''';') FROM mysql.user"
            dropping_all_users_stmts = client.execute_v2(
                dropping_all_users_stmt_gen, **kwargs
            ).get_result()
            dropping_all_users_stmts = [stmt[0] for stmt in dropping_all_users_stmts]
            for dropping_stmt in drop_all_roles_stmts + dropping_all_users_stmts:
                if not any(
                    user in dropping_stmt
                    for user in [
                        "root",
                        "mysql.sys",
                        "mysql.session",
                        "mysql.infoschema",
                        "mariadb.sys",
                        "mariadb.session",
                        "mariadb.infoschema",
                    ]
                ):
                    client.execute_v2(dropping_stmt, **kwargs)

        def init_from_empty(
            self,
            root_client: BasicClient,
            user_name_to_create: str,
            database_name_to_create: str,
            **kwargs,
        ):
            root_client.execute_v2(
                f"CREATE DATABASE {database_name_to_create}", **kwargs
            )
            root_client.execute_v2(f"CREATE USER {user_name_to_create}", **kwargs)
            root_client.execute_v2(
                f"CREATE ROLE `{user_name_to_create} role`", **kwargs
            )
            root_client.execute_v2(
                f"GRANT `{user_name_to_create} role` TO {user_name_to_create}", **kwargs
            )
            root_client.execute_v2(
                f"SET DEFAULT ROLE `{user_name_to_create} role` TO {user_name_to_create}",
                **kwargs,
            )
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
            **kwargs,
        ):
            self.clean(
                root_client, user_name_to_reset, database_name_to_reset, **kwargs
            )
            self.init_from_empty(
                root_client, user_name_to_reset, database_name_to_reset, **kwargs
            )

        def reset_all(
            self,
            root_client: BasicClient,
            user_name_to_reset: str,
            database_name_to_reset: str,
            **kwargs,
        ):
            self.clean_all(root_client)
            self.init_from_empty(
                root_client, user_name_to_reset, database_name_to_reset, **kwargs
            )

    class MetaQuery(Dialect.MetaQuery):
        def get_metaqueries(self, schema: str | None = "test") -> list[str]:
            queries = [
                "SELECT SUBSTRING_INDEX(USER(), '@', 1) AS name, 'USER' AS type, null AS parentname",
                "SELECT DISTINCT user AS name, 'USER' AS type, null AS parentname FROM mysql.user",
                "SELECT table_name AS name, 'TABLE' AS type, '' AS parentname FROM information_schema.tables WHERE table_type='BASE TABLE'"
                + (f" AND table_schema='{schema}'" if schema else ""),
                "SELECT column_name AS name, 'COLUMN' AS type, table_name AS parentname FROM information_schema.columns"
                + (f" WHERE table_schema='{schema}'" if schema else ""),
                "SELECT table_name AS name, 'VIEW' AS type, null AS parentname FROM information_schema.VIEWS"
                + (f" WHERE table_schema='{schema}'" if schema else ""),
                "SELECT event_name AS name, 'EVENT' AS type, null AS parentname FROM information_schema.events"
                + (f" WHERE event_schema='{schema}'" if schema else ""),
                "SELECT DISTINCT routine_name AS name, routine_type AS type, null AS parentname FROM information_schema.ROUTINES"
                + (f" WHERE routine_schema='{schema}'" if schema else ""),
                "SELECT trigger_name AS name, 'TRIGGER' AS type, null AS parentname FROM information_schema.triggers"
                + (f" WHERE trigger_schema='{schema}'" if schema else ""),
                "SELECT table_name AS name, 'STATISTICS' AS type, null AS parentname FROM information_schema.statistics"
                + (f" WHERE table_schema='{schema}'" if schema else ""),
                "SELECT SCHEMA_NAME AS name, 'SCHEMA' AS type, null AS parentname FROM information_schema.SCHEMATA",
            ]
            return queries

        def get_systable_names_query(self, version=0) -> str:
            return "SELECT concat(table_schema, '.', table_name) FROM information_schema.tables"

        def get_systable_names(self) -> list[str]:
            return get_mysql_system_tables()

    class HealthChecker(Dialect.HealthChecker):
        @classmethod
        def table_creation_testing_sqls(cls) -> list[str]:
            suffix = cls._random_identifier(8)
            return [
                "SHOW DATABASES",
                f"CREATE TABLE t{suffix} (x INT)",
                f"DROP TABLE t{suffix}",
            ]

    class GrantGenerator(MysqlGeneratorNormal):
        pass

    class RoleOperation(Dialect.RoleOperation):
        def create_role_stmt(self, role_name: str) -> str:
            return f"CREATE ROLE {role_name}"

        def drop_role_stmt(self, role_name: str) -> str:
            return f"DROP ROLE {role_name}"

        def grant_role_stmt(self, role_name: str, user_name: str) -> str:
            return f"GRANT {role_name} TO {user_name}"

        def revoke_role_stmt(self, role_name: str, user_name: str) -> str:
            return f"REVOKE {role_name} FROM {user_name}"

        def set_default_role_stmt(self, user_name: str, role_name: str) -> str:
            return f"SET DEFAULT ROLE {role_name} TO {user_name}"

        def unset_default_role_stmt(self, user_name: str) -> str:
            return f"SET DEFAULT ROLE NONE TO {user_name}"

        def enable_role_stmt(self, user_name: str, role_name: str) -> str:
            return f"SET ROLE {role_name}"

        def disable_role_stmt(self, user_name: str, role_name: str) -> str:
            return f"SET ROLE ALL EXCEPT {role_name}"

    class DockerOperation(Dialect.DockerOperation):
        DOCKER_PORT_NUMBER = 3306
        DOCKER_IMAGE_VERSION = "9.2.0"
        DOCKER_CONTAINER_NAME = "some-mysql"

        def __init__(self, dbms_cls=None):
            super().__init__(dbms_cls or MySQL)

    INITIAL_SAMPLE_STATEMENT = [
        None,
        "CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) );",
        "CREATE TABLE tbl2 ( my_2_col VARCHAR(255) );",
        "CREATE TABLE tbl3 ( my_3_col VARCHAR(255) );",
        "CREATE INDEX my_index ON tbl1 (my_1_col);",
        "CREATE TRIGGER my_trigger BEFORE INSERT ON tbl1 FOR EACH ROW INSERT INTO tbl2 SELECT * FROM tbl3;\n        INSERT INTO tbl1 VALUES (1, '2')",
        "CREATE VIEW my_view AS SELECT * FROM tbl2;",
        "CREATE EVENT my_event\n           ON SCHEDULE AT CURRENT_TIMESTAMP + INTERVAL 1 HOUR\n           DO INSERT INTO my_log (message, created_at) VALUES ('Event triggered', NOW());",
        "CREATE FUNCTION my_function1 (func_args_1 INT) RETURNS INT DETERMINISTIC BEGIN RETURN 1; END;",
        "DELIMITER $$\n           DROP FUNCTION IF EXISTS copy_tbl_func $$\n           CREATE FUNCTION copy_tbl_func (useless_arg INT) RETURNS INT DETERMINISTIC BEGIN INSERT INTO tbl2 SELECT my_2_col FROM tbl1; RETURN 1; END $$\n           SELECT copy_tbl_func(1) $$\n           DELIMITER ;\n           -- delimiter end",
        "CREATE PROCEDURE my_procedure() BEGIN SELECT CONCAT('Current Time: ', NOW()); END;",
        "CREATE SERVER my_server FOREIGN DATA WRAPPER mysql OPTIONS (HOST '127.0.0.1', DATABASE 'mysql', USER 'root');",
        'CREATE SPATIAL REFERENCE SYSTEM 912345 NAME \'my_custom_wgs_84\'\n           DEFINITION \'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AXIS["Latitude",NORTH],AXIS["Longitude",EAST]]\'\n           DESCRIPTION \'Custom WGS 84 geographic coordinate system\';',
        "CREATE TABLESPACE my_tablespace ADD DATAFILE 'my_tablespace_data.ibd' ENGINE=InnoDB;",
        "SELECT * FROM my_view;",
        "INSERT INTO tbl1 VALUES (1, '')",
        "INSERT INTO tbl2 VALUES (1)",
        "INSERT INTO tbl3 VALUES (1)",
        "INSERT INTO tbl1 VALUES (DEFAULT, DEFAULT)",
        "INSERT INTO tbl2 VALUES (DEFAULT)",
        "INSERT INTO tbl3 VALUES (DEFAULT)",
        "SELECT * FROM tbl1;",
        "SELECT * FROM tbl2;",
        "SELECT * FROM tbl3;",
    ]
    INITIAL_SAMPLE_STATEMENT_METADATA = [
        ("tbl1", "TABLE", ""),
        ("tbl2", "TABLE", ""),
        ("tbl3", "TABLE", ""),
        ("my_index", "INDEX", ""),
        ("my_trigger", "TRIGGER", ""),
        ("my_view", "VIEW", ""),
        ("my_1_col", "COLUMN", "tbl1"),
        ("my_2_col", "COLUMN", "tbl1"),
        ("my_3_col", "COLUMN", "tbl3"),
        ("my_2_col", "COLUMN", "tbl2"),
        ("my_2_col", "COLUMN", "my_view"),
        ("testuser", "USER", ""),
        ("my_db", "DATABASE", ""),
        ("my_function", "FUNCTION", ""),
        ("copy_tbl_func", "FUNCTION", ""),
        ("my_procedure", "PROCEDURE", ""),
        ("my_server", "SERVER", ""),
        ("912345", "SPATIAL REFERENCE SYSTEM", ""),
        ("my_tablespace", "TABLESPACE", ""),
        ("my_event", "EVENT", ""),
    ]
    DSN_NAME = "mysql"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="mysql", username="root", password="", database="mysql"
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="mysql", username="root", password="", database="test"
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="mysql", username="foooo", password="", database="test"
    )
    SQLGLOT_DIALECT = "mysql"

    @classmethod
    def reset_default_database_instance(
        cls,
        port_number: int = 3306,
        image_version: str = "9.2.0",
        container_name: str = "some-mysql-0",
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
                "MYSQL_ALLOW_EMPTY_PASSWORD=1",
                "-p",
                f"{port_number}:3306",
                f"mysql:{image_version}",
            ],
            check=True,
        )
        port_override = dict(port=port_number)
        init_config = {**cls.DEFAULT_INIT_CONFIG, **port_override}
        cls.wait_for_database_ready(
            config=init_config, max_wait_seconds=60, check_interval_seconds=2.0
        )
        cls._init_database_with_cleaner(
            init_config=port_override, test_config=port_override
        )


class MySQLInst(MySQL):
    DSN_NAME = "mysql-inst"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="mysql-inst", username="root", password="", database="mysql"
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="mysql-inst", username="root", password="", database="test"
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="mysql-inst", username="foooo", password="", database="test"
    )
