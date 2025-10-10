import sys
sys.modules["pybeacon.dialects.postgres"] = sys.modules[__name__]

import _import_hook
import logging, os
from pathlib import Path
from typing import Iterator
import subprocess, time
from langchain_community.document_loaders import DirectoryLoader
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from pybeacon import PYBEACON_ROOT_DIR
from pybeacon.clients.basic.basic_client import BasicClient
from pybeacon.dialects.dialect import Dialect
from pybeacon.generation.corpus import Corpus
from pybeacon.generation.corpus_parser.base_parser import SimpleParser
from pybeacon.beacon.metadata import StatementEx
from pybeacon.logging.configure import get_console_logger
from pybeacon.generation.grant_stmt.dbms.postgres import PostgresGeneratorFull

console_logger = get_console_logger(logger_name=__name__)
console_logger._logger.setLevel(logging.DEBUG)


class PostgreSQL(Dialect):
    TEST_DATABASE = "beacon_testdb"
    TEST_USER = "beacon_guest"
    TEST_PASSWORD = "Guest@123"

    class DocumentLoader(Dialect.DocumentLoader):
        def lazy_load(self) -> Iterator[Document]:
            loader = DirectoryLoader(str(PostgreSQL.DOC_PATH))
            for doc in loader.lazy_load():
                doc.metadata["source"] = Path(doc.metadata["source"]).name
                yield doc

    class CorpusLoader(Dialect.CorpusLoader):
        def lazy_load(self) -> Iterator[Corpus]:
            simple_parser = SimpleParser(str(PostgreSQL.CORPUS_PATH))
            for file in simple_parser.get_relative_file_list():
                stmts = simple_parser.parse_sql_statements(file)
                stmtex_list = [StatementEx(stmt) for stmt in stmts]
                yield Corpus(name=file, stmtex_list=stmtex_list)

    class CorpusParser(Dialect.CorpusParser):
        def __init__(self):
            super().__init__(str(PostgreSQL.CORPUS_PATH))

    class DatabaseCleaner(Dialect.DatabaseCleaner):
        def clean(
            self,
            root_client: BasicClient,
            user_name_to_drop: str,
            database_name_to_drop: str,
            **kwargs,
        ):
            exec_pg = dict(kwargs)
            exec_pg["database"] = "postgres"
            root_client.execute_v2(
                f"DROP DATABASE IF EXISTS {database_name_to_drop}", **exec_pg
            )
            root_client.execute_v2(
                f"DROP USER IF EXISTS {user_name_to_drop}", **exec_pg
            )

        def clean_all(self, root_client: BasicClient, **kwargs):
            client = root_client
            exec_pg = dict(kwargs)
            exec_pg["database"] = "postgres"
            ret = client.execute_v2(
                "SELECT datname FROM pg_database WHERE datistemplate = false AND datname NOT IN ('postgres')",
                **exec_pg,
            )
            ret.assert_succ()
            existing_databases = ret.get_result()
            console_logger.debug(
                f"Drop existing databases...", existing_databases=existing_databases
            )
            for database_name_tuple in existing_databases:
                database_name = database_name_tuple[0]
                if database_name not in {"postgres", "template0", "template1"}:
                    client.execute_v2(
                        f"DROP DATABASE IF EXISTS {database_name}", **exec_pg
                    )
            existing_roles = client.execute_v2(
                "SELECT rolname FROM pg_roles WHERE rolname NOT LIKE 'pg_%' AND rolname != 'postgres'",
                **exec_pg,
            ).get_result()
            existing_roles = [role[0] for role in existing_roles]
            console_logger.debug(
                f"Drop existing roles...", existing_roles=existing_roles
            )
            for role_name in existing_roles:
                client.execute_v2(f"DROP ROLE IF EXISTS {role_name}", **exec_pg)

        def init_from_empty(
            self,
            root_client: BasicClient,
            user_name_to_create: str,
            database_name_to_create: str,
            **kwargs,
        ):
            exec_pg = dict(kwargs)
            exec_pg["database"] = "postgres"
            root_client.execute_v2(
                f"CREATE DATABASE {database_name_to_create}", **exec_pg
            ).assert_succ()
            root_client.execute_v2(
                f"CREATE USER {user_name_to_create} WITH PASSWORD '{PostgreSQL.TEST_PASSWORD}'",
                **exec_pg,
            ).assert_succ()
            root_client.execute_v2(
                f"GRANT ALL PRIVILEGES ON DATABASE {database_name_to_create} TO {user_name_to_create}",
                **exec_pg,
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
            self.clean_all(root_client, **kwargs)
            self.init_from_empty(
                root_client, user_name_to_reset, database_name_to_reset, **kwargs
            )

    class MetaQuery(Dialect.MetaQuery):
        def get_metaqueries(self, schema: str | None = "public") -> list[str]:
            queries = [
                "SELECT usename AS name, 'USER' AS type, null AS parentname FROM pg_user",
                "SELECT rolname AS name, 'ROLE' AS type, null AS parentname FROM pg_roles",
                "SELECT tablename AS name, 'TABLE' AS type, schemaname AS parentname FROM pg_tables"
                + (f" WHERE schemaname = '{schema}'" if schema else ""),
                "SELECT attname AS name, 'COLUMN' AS type, attrelid::regclass::text AS parentname FROM pg_attribute a "
                + "JOIN pg_class c ON c.oid = a.attrelid "
                + "JOIN pg_namespace n ON n.oid = c.relnamespace "
                + "WHERE a.attnum > 0 AND NOT a.attisdropped"
                + (f" AND n.nspname = '{schema}'" if schema else ""),
                "SELECT viewname AS name, 'VIEW' AS type, schemaname AS parentname FROM pg_views"
                + (f" WHERE schemaname = '{schema}'" if schema else ""),
                "SELECT proname AS name, 'FUNCTION' AS type, n.nspname AS parentname FROM pg_proc p "
                + "JOIN pg_namespace n ON n.oid = p.pronamespace "
                + "WHERE p.prokind = 'f'"
                + (f" AND n.nspname = '{schema}'" if schema else ""),
                "SELECT proname AS name, 'PROCEDURE' AS type, n.nspname AS parentname FROM pg_proc p "
                + "JOIN pg_namespace n ON n.oid = p.pronamespace "
                + "WHERE p.prokind = 'p'"
                + (f" AND n.nspname = '{schema}'" if schema else ""),
                "SELECT tgname AS name, 'TRIGGER' AS type, c.relname AS parentname FROM pg_trigger t "
                + "JOIN pg_class c ON c.oid = t.tgrelid "
                + "JOIN pg_namespace n ON n.oid = c.relnamespace "
                + "WHERE NOT t.tgisinternal"
                + (f" AND n.nspname = '{schema}'" if schema else ""),
                "SELECT indexname AS name, 'INDEX' AS type, schemaname AS parentname FROM pg_indexes"
                + (f" WHERE schemaname = '{schema}'" if schema else ""),
                "SELECT sequence_name AS name, 'SEQUENCE' AS type, sequence_schema AS parentname FROM information_schema.sequences"
                + (f" WHERE sequence_schema = '{schema}'" if schema else ""),
                "SELECT typname AS name, 'TYPE' AS type, n.nspname AS parentname FROM pg_type t "
                + "JOIN pg_namespace n ON n.oid = t.typnamespace "
                + "WHERE t.typtype = 'c'"
                + (f" AND n.nspname = '{schema}'" if schema else ""),
                "SELECT nspname AS name, 'SCHEMA' AS type, null AS parentname FROM pg_namespace "
                + "WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'",
            ]
            return queries

        def get_systable_names_query(self, version=0) -> str:
            return "SELECT table_schema || '.' || table_name FROM information_schema.tables WHERE table_schema IN ('pg_catalog', 'information_schema')"

        def get_systable_names(self) -> list[str]:
            schemas = {
                "information_schema": [
                    "administrable_role_authorizations",
                    "applicable_roles",
                    "attributes",
                    "character_sets",
                    "check_constraint_routine_usage",
                    "check_constraints",
                    "collation_character_set_applicability",
                    "collations",
                    "column_column_usage",
                    "column_domain_usage",
                    "column_options",
                    "column_privileges",
                    "column_udt_usage",
                    "columns",
                    "constraint_column_usage",
                    "constraint_table_usage",
                    "data_type_privileges",
                    "domain_constraints",
                    "domain_udt_usage",
                    "domains",
                    "element_types",
                    "enabled_roles",
                    "foreign_data_wrapper_options",
                    "foreign_data_wrappers",
                    "foreign_server_options",
                    "foreign_servers",
                    "foreign_table_options",
                    "foreign_tables",
                    "information_schema_catalog_name",
                    "key_column_usage",
                    "parameters",
                    "referential_constraints",
                    "role_column_grants",
                    "role_routine_grants",
                    "role_table_grants",
                    "role_usage_grants",
                    "routine_column_usage",
                    "routine_privileges",
                    "routine_routine_usage",
                    "routine_sequence_usage",
                    "routine_table_usage",
                    "routines",
                    "schemata",
                    "sequences",
                    "sql_features",
                    "sql_implementation_info",
                    "sql_languages",
                    "sql_packages",
                    "sql_parts",
                    "sql_sizing",
                    "sql_sizing_profiles",
                    "table_constraints",
                    "table_privileges",
                    "tables",
                    "transforms",
                    "triggered_update_columns",
                    "triggers",
                    "udt_privileges",
                    "usage_privileges",
                    "user_defined_types",
                    "user_mapping_options",
                    "user_mappings",
                    "view_column_usage",
                    "view_routine_usage",
                    "view_table_usage",
                    "views",
                ],
                "pg_catalog": [
                    "pg_aggregate",
                    "pg_am",
                    "pg_amop",
                    "pg_amproc",
                    "pg_attrdef",
                    "pg_attribute",
                    "pg_auth_members",
                    "pg_authid",
                    "pg_available_extension_versions",
                    "pg_available_extensions",
                    "pg_available_triggers",
                    "pg_cast",
                    "pg_class",
                    "pg_collation",
                    "pg_constraint",
                    "pg_conversion",
                    "pg_database",
                    "pg_db_role_setting",
                    "pg_default_acl",
                    "pg_depend",
                    "pg_description",
                    "pg_enum",
                    "pg_event_trigger",
                    "pg_extension",
                    "pg_foreign_data_wrapper",
                    "pg_foreign_server",
                    "pg_foreign_table",
                    "pg_index",
                    "pg_indexes",
                    "pg_inherits",
                    "pg_init_privs",
                    "pg_language",
                    "pg_largeobject",
                    "pg_largeobject_metadata",
                    "pg_namespace",
                    "pg_opclass",
                    "pg_operator",
                    "pg_opfamily",
                    "pg_partitioned_table",
                    "pg_pltemplate",
                    "pg_policy",
                    "pg_proc",
                    "pg_publication",
                    "pg_publication_rel",
                    "pg_range",
                    "pg_replication_origin",
                    "pg_replication_slots",
                    "pg_rewrite",
                    "pg_seclabel",
                    "pg_sequence",
                    "pg_sequences",
                    "pg_shdepend",
                    "pg_shdescription",
                    "pg_shseclabel",
                    "pg_stat_activity",
                    "pg_stat_all_indexes",
                    "pg_stat_all_tables",
                    "pg_stat_archiver",
                    "pg_stat_bgwriter",
                    "pg_stat_database",
                    "pg_stat_database_conflicts",
                    "pg_stat_gssapi",
                    "pg_stat_progress_analyze",
                    "pg_stat_progress_basebackup",
                    "pg_stat_progress_cluster",
                    "pg_stat_progress_copy",
                    "pg_stat_progress_create_index",
                    "pg_stat_progress_vacuum",
                    "pg_stat_replication",
                    "pg_stat_replication_slots",
                    "pg_stat_slru",
                    "pg_stat_ssl",
                    "pg_stat_subscription",
                    "pg_stat_sys_indexes",
                    "pg_stat_sys_tables",
                    "pg_stat_user_functions",
                    "pg_stat_user_indexes",
                    "pg_stat_user_tables",
                    "pg_stat_wal_receiver",
                    "pg_stat_xact_all_tables",
                    "pg_stat_xact_sys_tables",
                    "pg_stat_xact_user_functions",
                    "pg_stat_xact_user_tables",
                    "pg_statio_all_indexes",
                    "pg_statio_all_sequences",
                    "pg_statio_all_tables",
                    "pg_statio_sys_indexes",
                    "pg_statio_sys_sequences",
                    "pg_statio_sys_tables",
                    "pg_statio_user_indexes",
                    "pg_statio_user_sequences",
                    "pg_statio_user_tables",
                    "pg_subscription",
                    "pg_subscription_rel",
                    "pg_tablespace",
                    "pg_timezone_abbrevs",
                    "pg_timezone_names",
                    "pg_transform",
                    "pg_trigger",
                    "pg_ts_config",
                    "pg_ts_config_map",
                    "pg_ts_dict",
                    "pg_ts_parser",
                    "pg_ts_template",
                    "pg_type",
                    "pg_user_mapping",
                    "pg_views",
                ],
            }
            tables = [
                f"{schema}.{table}" for schema in schemas for table in schemas[schema]
            ]
            return tables

    class GrantGenerator(PostgresGeneratorFull):
        pass

    class RoleOperation(Dialect.RoleOperation):
        def create_role_stmt(self, role_name: str) -> str:
            return f"CREATE ROLE {role_name}"

        def drop_role_stmt(self, role_name: str) -> str:
            return f"DROP ROLE IF EXISTS {role_name}"

        def grant_role_stmt(self, role_name: str, user_name: str) -> str:
            return f"GRANT {role_name} TO {user_name}"

        def revoke_role_stmt(self, role_name: str, user_name: str) -> str:
            return f"REVOKE {role_name} FROM {user_name}"

        def set_default_role_stmt(self, user_name: str, role_name: str) -> str:
            return f"ALTER USER {user_name} SET DEFAULT ROLE {role_name}"

        def unset_default_role_stmt(self, user_name: str) -> str:
            return f"ALTER USER {user_name} SET DEFAULT ROLE NONE"

        def enable_role_stmt(self, user_name: str, role_name: str) -> str:
            return f"SET ROLE {role_name}"

        def disable_role_stmt(self, user_name: str, role_name: str) -> str:
            return f"SET ROLE NONE"

    INITIAL_SAMPLE_STATEMENT = [
        "CREATE TABLE tbl1 ( my_1_col INT, my_2_col VARCHAR(255) );",
        "CREATE TABLE tbl2 ( my_2_col VARCHAR(255) );",
        "CREATE TABLE tbl3 ( my_3_col VARCHAR(255) );",
        "CREATE INDEX my_index ON tbl1 (my_1_col);",
        "CREATE OR REPLACE FUNCTION my_trigger_function() RETURNS TRIGGER AS $$\n           BEGIN\n             INSERT INTO tbl2 SELECT NEW.my_2_col;\n             RETURN NEW;\n           END;\n           $$ LANGUAGE plpgsql;\n           CREATE TRIGGER my_trigger BEFORE INSERT ON tbl1 FOR EACH ROW EXECUTE FUNCTION my_trigger_function();\n           INSERT INTO tbl1 VALUES (1, '2');",
        "CREATE VIEW my_view AS SELECT * FROM tbl2;",
        "CREATE OR REPLACE FUNCTION my_function1(func_args_1 INT) RETURNS INT AS $$\n           BEGIN\n             RETURN 1;\n           END;\n           $$ LANGUAGE plpgsql;",
        "CREATE OR REPLACE FUNCTION copy_tbl_func(useless_arg INT) RETURNS INT AS $$\n           BEGIN\n             INSERT INTO tbl2 SELECT my_2_col FROM tbl1;\n             RETURN 1;\n           END;\n           $$ LANGUAGE plpgsql;\n           SELECT copy_tbl_func(1);",
        "CREATE OR REPLACE PROCEDURE my_procedure() AS $$\n           BEGIN\n             RAISE NOTICE 'Current Time: %', NOW();\n           END;\n           $$ LANGUAGE plpgsql;",
        "CREATE EXTENSION IF NOT EXISTS postgres_fdw;\n           CREATE SERVER my_server FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host '127.0.0.1', dbname 'postgres');",
        "CREATE SEQUENCE my_sequence START WITH 1 INCREMENT BY 1;",
        "CREATE DOMAIN my_domain AS VARCHAR(50) CHECK (VALUE ~ '^[A-Z][a-z]+$');",
        "CREATE TYPE my_type AS (id INT, name VARCHAR(100));",
        "CREATE TABLESPACE my_tablespace LOCATION '/tmp/pg_tablespace';",
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
        ("my_function1", "FUNCTION", ""),
        ("copy_tbl_func", "FUNCTION", ""),
        ("my_procedure", "PROCEDURE", ""),
        ("my_server", "SERVER", ""),
        ("my_sequence", "SEQUENCE", ""),
        ("my_domain", "DOMAIN", ""),
        ("my_type", "TYPE", ""),
        ("my_tablespace", "TABLESPACE", ""),
        ("my_trigger_function", "FUNCTION", ""),
    ]
    DSN_NAME = "postgres"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="postgres",
        username="postgres",
        password="mysecretpassword",
        database="postgres",
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="postgres",
        username="postgres",
        password="mysecretpassword",
        database=TEST_DATABASE,
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="postgres",
        username=TEST_USER,
        password=TEST_PASSWORD,
        database=TEST_DATABASE,
    )
    SQLGLOT_DIALECT = "postgres"

    @classmethod
    def reset_default_database_instance(
        cls,
        port_number: int = 5432,
        image_version: str = "18.1",
        container_name: str = "postgres-0",
    ) -> None:
        subprocess.run(["docker", "rm", "-f", container_name], check=False)
        time.sleep(2)
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-p",
                f"{port_number}:5432",
                "-e",
                "POSTGRES_PASSWORD=mysecretpassword",
                f"postgres:{image_version}",
            ],
            check=True,
        )
        port_override = dict(port=port_number)
        init_config = {**cls.DEFAULT_INIT_CONFIG, **port_override}
        cls.wait_for_database_ready(
            config=init_config, max_wait_seconds=30, check_interval_seconds=2.0
        )
        try:
            subprocess.run(
                ["docker", "exec", container_name, "mkdir", "-p", "/tmp/pg_tablespace"],
                check=False,
            )
            subprocess.run(
                [
                    "docker",
                    "exec",
                    container_name,
                    "chown",
                    "postgres:postgres",
                    "/tmp/pg_tablespace",
                ],
                check=False,
            )
        except Exception:
            pass

    class DockerOperation(Dialect.DockerOperation):
        DOCKER_PORT_NUMBER = 5432
        DOCKER_IMAGE_VERSION = "18.1"
        DOCKER_CONTAINER_NAME = "postgres"

        def __init__(self, dbms_cls=None):
            super().__init__(dbms_cls or PostgreSQL)


class PostgreSQLInst(PostgreSQL):
    DSN_NAME = "postgres-inst"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="postgres-inst", username="postgres", password="", database="postgres"
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="postgres-inst", username="postgres", password="", database="postgres"
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="postgres-inst", username="foooo", password="", database="test"
    )
