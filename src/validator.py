import sys
sys.modules["pybeacon.test_oracle.system_table_inspector"] = sys.modules[__name__]

import _import_hook
import datetime, os, re, string
from typing import List, Iterator, Iterable
from pybeacon.clients.basic.basic_client import BasicClient
from pybeacon.clients.basic.result_set import ResultSet
from pybeacon.clients.universe.custom_ini_client import CustomIniClient
from pybeacon.clients.universe.metadata_analysis_client import (
    get_metadata_info_from_queries,
)
from pybeacon.clients.universe.user_switch_client import UserSwitchClient
from pybeacon.dialects.mysql import MySQL

package_name = __package__


class SystemTableInspector:
    def __init__(self, dsn: str, database: str, system_table_names: List[str]) -> None:
        self.dsn_name = dsn
        self.database_name = database
        self.system_table_names = system_table_names

    def get_system_tables_content(self, user: str) -> str:
        user_switch_client = UserSwitchClient(
            CustomIniClient,
            dsn_name=self.dsn_name,
            username=user,
            database=self.database_name,
        )
        combined_system_content = ""
        for table_name in self.system_table_names:
            is_succ, result, errlog = user_switch_client.execute(
                "SELECT * FROM " + table_name
            )
            if is_succ:
                combined_system_content += str(result)
            else:
                print("Permission denied to access system table " + table_name)
        return combined_system_content

    def filter_known_objects_in_system_tables(
        self, known_objects: List[str], combined_system_content: str
    ) -> List[str]:
        filtered_objects = []
        for obj in known_objects:
            if obj in combined_system_content:
                filtered_objects.append(obj)
        return filtered_objects

    def filter_unknown_objects_in_system_tables(
        self, known_objects: List[str], combined_system_content: str
    ) -> List[str]:
        filtered_objects = []
        for obj in known_objects:
            if obj not in combined_system_content:
                filtered_objects.append(obj)
        return filtered_objects

    def check_statement_and_error(
        self,
        statement: str,
        execution_result: str,
        error_message: str,
        combined_system_content: str,
        known_objects: List[str],
    ) -> bool:
        result_objects_set, error_objects_set = set(), set()
        result_objects, error_objects = [], []
        if execution_result != "":
            for obj in known_objects:
                pattern = "\\b" + re.escape(obj) + "\\b"
                obj_found = False
                if re.search(pattern, execution_result):
                    obj_found = True
                if obj_found and obj not in result_objects_set:
                    result_objects.append(obj)
                    result_objects_set.add(obj)
            print("------------------------------------------------------------")
            print("statement = " + statement)
            print("result = " + execution_result)
            print("result objects = ", result_objects)
            print("------------------------------------------------------------")
        elif error_message != "":
            for obj in known_objects:
                pattern = "\\b" + re.escape(obj) + "\\b"
                obj_found = False
                if re.search(pattern, error_message):
                    obj_found = True
                if obj_found and obj not in error_objects_set:
                    error_objects.append(obj)
                    error_objects_set.add(obj)
            print("------------------------------------------------------------")
            print("statement = " + statement)
            print("errormsg = " + error_message)
            print("error objects = ", error_objects)
            print("------------------------------------------------------------")
        output_dir = f"out/{self.dsn_name}"
        os.makedirs(output_dir, exist_ok=True)
        illegal_objects = []
        message = ""
        for obj in self.filter_unknown_objects_in_system_tables(
            result_objects, combined_system_content
        ):
            if obj not in statement:
                illegal_objects.append(obj)
                message = execution_result
        for obj in self.filter_unknown_objects_in_system_tables(
            error_objects, combined_system_content
        ):
            if obj not in statement:
                illegal_objects.append(obj)
                message = error_message
        if not illegal_objects:
            return False
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"case_{current_time}.txt"
        output_path = os.path.join(output_dir, output_file)
        content = f"""SQL:
{statement}

Output:
{message}

Illegal objects:
"""
        content += str(illegal_objects)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True


class SystemTableInspectorCustom:
    default_metaquery_creator = MySQL.MetaQuery()
    default_whitelist = {
        *[chr(i) for i in range(32, 127)],
        "USER",
        "MYSQL",
        "STARROCKS",
        "TIDB",
        "OCEANBASE",
        "SYS",
        "SYSDBA",
        "ROOT",
        "INFORMATION_SCHEMA",
        "TEST",
        "PERFORMANCE_SCHEMA",
        "PRIVILEGES",
    }
    change_metadata_words = {
        "CREATE",
        "INSERT",
        "DROP",
        "ALTER",
        "RENAME",
        "TRUNCATE",
        "REPLACE",
        "GRANT",
        "REVOKE",
    }
    AVALIABLE_MODE = [
        "default",
        "sql",
        "errmsg",
        "result",
        "sql_no_allowlist",
        "errmsg_no_allowlist",
    ]

    def __init__(
        self,
        client: BasicClient,
        metadata_queries: list[str] | None = None,
        object_name_whitelist: Iterable[str] | None = None,
        client_kwargs: dict = None,
        object_name_filter_regex: str | None = None,
    ):
        (self.client): BasicClient = client
        (self.metadata_queries): list[str] | None = metadata_queries
        (self.known_object_cache): set[str] | None = None
        self.client_kwargs = client_kwargs if client_kwargs else {}
        self.object_name_filter_regex = object_name_filter_regex
        if object_name_whitelist is None:
            (self.object_name_whitelist): set[str] = self.default_whitelist.copy()
        else:
            (self.object_name_whitelist): set[str] = (
                set(object_name_whitelist) | self.default_whitelist
            )
        if metadata_queries is None:
            assert (
                "database" in client_kwargs
            ), "database must be provided in client_kwargs if metadata_queries is None"
            self.metadata_queries = self.default_metaquery_creator.get_metaqueries(
                schema=client_kwargs["database"]
            )

    def get_known_objects(self) -> set[str]:
        metadata_tuples = get_metadata_info_from_queries(
            self.client, self.metadata_queries, **self.client_kwargs
        )
        known_objects = set(str(row[0]).upper() for row in metadata_tuples)
        known_objects -= self.object_name_whitelist
        if self.object_name_filter_regex:
            import re

            regex_pattern = re.compile(self.object_name_filter_regex, re.IGNORECASE)
            known_objects = {obj for obj in known_objects if regex_pattern.search(obj)}
        self.known_object_cache = known_objects
        return known_objects

    def get_known_objects_cache(self, flush=False) -> set[str]:
        if self.known_object_cache is None or flush:
            self.known_object_cache = self.get_known_objects()
        return self.known_object_cache

    def check_statement_change_metadata(self, statement: str) -> bool:
        statement_upper = statement.upper()
        for word in self.change_metadata_words:
            if word in statement_upper:
                self.get_known_objects_cache(flush=True)
                return True
        return False

    @staticmethod
    def trivial_stmt(stmt: str, result: list[tuple] | None) -> bool:
        if result is None:
            return False
        pattern = "SELECT (@.+?, )*(@.+)"
        match_result = re.match(pattern, stmt)
        if match_result:
            all_none = True
            for row in result:
                if not all(element == "None" for element in row):
                    all_none = False
                    break
            if all_none:
                return True
        pattern = "PREPARE .*? FROM '.*?'"
        match_result = re.match(pattern, stmt)
        if match_result and result == []:
            return True
        return False

    @staticmethod
    def check_execution_result(
        stmt: str, output: str, known_objects: set[str], mode="default"
    ) -> set[str]:
        output = output.upper()
        stmt_upper = stmt.upper()
        illegal_objects = set()
        for obj in known_objects:
            if SystemTableInspectorCustom.contains(obj, output):
                if mode != "errmsg_no_allowlist":
                    if obj.upper() in stmt_upper:
                        continue
                illegal_objects.add(obj)
        return illegal_objects

    @staticmethod
    def contains(object_name: str, text: str) -> bool:
        return re.search(rf"\b{re.escape(object_name)}\b", text) is not None

    @staticmethod
    def contains_except_quotes(object_name: str, text: str) -> bool:
        return (
            re.search(
                "(?<!['\\\"])\\b{}\\b(?!['\\\"])".format(re.escape(object_name)), text
            )
            is not None
        )

    @staticmethod
    def check_sql_statement(stmt: str, known_objects: set[str]) -> set[str]:
        illegal_objects = set()
        for obj in known_objects:
            if (
                SystemTableInspectorCustom.contains_except_quotes(obj, stmt)
                and obj not in illegal_objects
            ):
                illegal_objects.add(obj)
        return illegal_objects

    @staticmethod
    def validate_statement_system_consistency(
        testuser_result_set: ResultSet,
        test_sys_inspector: "SystemTableInspectorCustom",
        root_sys_inspector: "SystemTableInspectorCustom",
        auto_flush: bool = True,
        force_flush: bool = False,
        mode="default",
    ) -> set[str]:
        if force_flush:
            test_sys_inspector.get_known_objects_cache(flush=True)
            root_sys_inspector.get_known_objects_cache(flush=True)
        elif auto_flush:
            test_sys_inspector.check_statement_change_metadata(testuser_result_set.stmt)
            root_sys_inspector.check_statement_change_metadata(testuser_result_set.stmt)
        stmt = testuser_result_set.stmt
        known_objects = (
            root_sys_inspector.get_known_objects_cache()
            - test_sys_inspector.get_known_objects_cache()
        )
        illegal_objects_in_output = set()
        result_v2 = testuser_result_set
        if result_v2.is_succ():
            if mode in ["default", "result"]:
                output = str(result_v2.get_result())
                illegal_objects_in_output = (
                    SystemTableInspectorCustom.check_execution_result(
                        stmt, output, known_objects, mode
                    )
                )
        elif mode in ["default", "errmsg", "errmsg_no_allowlist"]:
            output = result_v2.get_errmsg()[0]
            illegal_objects_in_output = (
                SystemTableInspectorCustom.check_execution_result(
                    stmt, output, known_objects, mode
                )
            )

        def apply_sql_statement_checking():
            nonlocal illegal_objects_in_output
            illegal_objects_stmt = SystemTableInspectorCustom.check_sql_statement(
                stmt, known_objects
            )
            illegal_objects_in_output |= illegal_objects_stmt

        if result_v2.is_succ():
            if mode in ["default", "sql", "sql_no_allowlist"]:
                if mode != "sql_no_allowlist":
                    if not SystemTableInspectorCustom.trivial_stmt(
                        stmt, result_v2.get_result()
                    ):
                        apply_sql_statement_checking()
                else:
                    apply_sql_statement_checking()
        return illegal_objects_in_output
