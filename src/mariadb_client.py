import sys
sys.modules["pybeacon.dialects.mariadb"] = sys.modules[__name__]

import _import_hook
from pathlib import Path
from typing import Iterator, List, Dict
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from pybeacon import PYBEACON_ROOT_DIR
import subprocess, time
from pybeacon.dialects.dialect import Dialect
from pybeacon.dialects.mysql import MySQL
from pybeacon.generation.corpus import Corpus
from pybeacon.beacon.metadata import StatementEx
from pybeacon.logging.configure import get_console_logger
from pybeacon.dialects.constants import get_mariadb_system_tables

console_logger = get_console_logger(logger_name=__name__)


class MariaDB(MySQL):
    DSN_NAME = "mariadb"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="mariadb", username="root", password="", database="mysql"
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="mariadb", username="root", password="", database="test"
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="mariadb", username="foooo", password="", database="test"
    )

    class DockerOperation(MySQL.DockerOperation):
        DOCKER_PORT_NUMBER = 4306
        DOCKER_IMAGE_VERSION = "12.1.1-rc"
        DOCKER_CONTAINER_NAME = "some-mariadb"

        def __init__(self, dbms_cls=None):
            super().__init__(dbms_cls or MariaDB)

    @classmethod
    def reset_default_database_instance(
        cls,
        port_number: int = 4306,
        image_version: str = "12.1.1-rc",
        container_name: str = "some-mariadb-0",
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
                "--env",
                "MARIADB_ALLOW_EMPTY_ROOT_PASSWORD=1",
                "--env",
                "MYSQL_ALLOW_EMPTY_PASSWORD=1",
                "-p",
                f"{port_number}:3306",
                f"mariadb:{image_version}",
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

    class MetaQuery(MySQL.MetaQuery):
        def get_systable_names(self) -> list[str]:
            return get_mariadb_system_tables()
