import sys
sys.modules["pybeacon.dialects.oceanbase"] = sys.modules[__name__]

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
from pybeacon.dialects.constants import get_oceanbase_system_tables

console_logger = get_console_logger(logger_name=__name__)


class OceanBase(MySQL):
    DSN_NAME = "oceanbase"
    DEFAULT_INIT_CONFIG = dict(
        dsn_name="oceanbase", username="root", password="", database="mysql"
    )
    DEFAULT_ROOT_CONFIG = dict(
        dsn_name="oceanbase", username="root", password="", database="test"
    )
    DEFAULT_TEST_CONFIG = dict(
        dsn_name="oceanbase", username="foooo", password="", database="test"
    )

    class MetaQuery(MySQL.MetaQuery):
        def get_systable_names(self) -> list[str]:
            return get_oceanbase_system_tables()

    @classmethod
    def reset_default_database_instance(
        cls,
        port_number: int = 2881,
        image_version: str = "4.3.5.3-103000092025080818",
        container_name: str = "some-oceanbase-0",
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
                "MODE=slim",
                "-p",
                f"{port_number}:2881",
                f"oceanbase/oceanbase-ce:{image_version}",
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
        DOCKER_PORT_NUMBER = 2881
        DOCKER_IMAGE_VERSION = "4.3.5.1-101010042025042417"
        DOCKER_CONTAINER_NAME = "some-oceanbase"

        def __init__(self, dbms_cls=None):
            super().__init__(dbms_cls or OceanBase)

    INITIAL_SAMPLE_STATEMENT = [
        "CREATE TABLE tbl1 (col1 INT);",
        "INSERT INTO tbl1 (col1) VALUES (10);",
    ]
    INITIAL_SAMPLE_STATEMENT_METADATA = [
        ("tbl1", "TABLE", ""),
        ("col1", "COLUMN", "tbl1"),
    ]


if __name__ == "__main__":
    a = OceanBase()
    print("OceanBase dialect loaded successfully.")
    print(f"LLM Corpus Object Types: {OceanBase.LLM_CORPUS_OBJECT_TYPES}")
    for obj_type in OceanBase.LLM_CORPUS.object_types:
        print(
            f"Object Type: {obj_type.object_type_name}, Description: {obj_type.description}"
        )
