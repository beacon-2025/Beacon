import sys
sys.modules["pybeacon.dialects.starrocks"] = sys.modules[__name__]

import _import_hook
from pathlib import Path
from typing import Iterator, List, Dict
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from pybeacon import PYBEACON_ROOT_DIR
import subprocess, time
from pybeacon.clients.basic.basic_client import BasicClient
from pybeacon.dialects.dialect import Dialect
from pybeacon.dialects.mysql import MySQL
from pybeacon.generation.corpus import Corpus
from pybeacon.generation.grant_stmt.dbms.starrocks import StarrocksGrantGenerator
from pybeacon.beacon.metadata import StatementEx
from pybeacon.logging.configure import get_console_logger
from pybeacon.dialects.constants import get_starrocks_system_tables

console_logger = get_console_logger(logger_name=__name__)


class StarRocks(MySQL):
    class DatabaseCleaner(MySQL.DatabaseCleaner):
        def clean_all(self, root_client: BasicClient, **kwargs):
            client = root_client
            existing_databases = client.execute_v2(
                "SHOW DATABASES", **kwargs
            ).get_result()
            console_logger.debug(
                f"Drop existing databases...", existing_databases=existing_databases
            )
            for database_name_tuple in existing_databases:
                database_name = database_name_tuple[0]
                client.execute_v2(f"DROP DATABASE {database_name}", **kwargs)
            existing_users = client.execute_v2("SHOW USERS", **kwargs).get_result()
            existing_users = [user[0] for user in existing_users]
            console_logger.debug(
                f"Drop existing users...", existing_users=existing_users
            )
            for user in existing_users:
                if not any(
                    username in user
                    for username in [
                        "root",
                        "mysql.sys",
                        "mysql.session",
                        "mysql.infoschema",
                    ]
                ):
                    client.execute_v2(f"DROP USER {user}", **kwargs).assert_succ()

    class GrantGenerator(StarrocksGrantGenerator):
        pass

    DSN_NAME = "starrocks"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="starrocks", username="root", password="", database="sys"
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="starrocks", username="root", password="", database="test"
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="starrocks", username="foooo", password="", database="test"
    )
    SQLGLOT_DIALECT = "starrocks"

    class MetaQuery(MySQL.MetaQuery):
        def get_systable_names(self) -> list[str]:
            return get_starrocks_system_tables()

    @classmethod
    def reset_default_database_instance(
        cls,
        port_number: int = 9030,
        image_version: str = "3.3.5",
        container_name: str = "some-starrocks-0",
    ) -> None:
        subprocess.run(["docker", "container", "rm", "-f", container_name], check=False)
        time.sleep(5)
        subprocess.run(
            [
                "docker",
                "run",
                "-p",
                f"{port_number}:9030",
                "-p",
                "8030:8030",
                "-p",
                "8040:8040",
                "-itd",
                "--name",
                container_name,
                f"starrocks/allin1-ubuntu:{image_version}",
            ],
            check=True,
        )
        port_override = dict(port=port_number)
        init_config = {**cls.DEFAULT_INIT_CONFIG, **port_override}
        cls.wait_for_database_ready(
            config=init_config, max_wait_seconds=180, check_interval_seconds=5.0
        )
        cls._init_database_with_cleaner(
            init_config=port_override, test_config=port_override
        )

    class DockerOperation(MySQL.DockerOperation):
        DOCKER_PORT_NUMBER = 9030
        DOCKER_IMAGE_VERSION = "3.3.5"
        DOCKER_CONTAINER_NAME = "some-starrocks"

        def __init__(self, dbms_cls=None):
            super().__init__(dbms_cls or StarRocks)
