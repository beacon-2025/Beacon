import sys
sys.modules["pybeacon.beacon.generator_normalize"] = sys.modules[__name__]

import _import_hook
import random, time, argparse, re
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Type
from pybeacon.clients.basic.basic_client import BasicClient
from pybeacon.dialects.dialect import Dialect
from pybeacon.beacon.metadata import (
    MetadataGraph,
    StatementEx,
    substitute_statement_by_current_metadata_no_throw,
)
from pybeacon.beacon.sql_trie_generator import SQLTrieGenerator


def _remove_sql_comments(sql: str) -> str:
    sql = re.sub("--.*?(?=\\n|$)", "", sql)
    sql = re.sub("/\\*.*?\\*/", "", sql, flags=re.DOTALL)
    return sql.strip()


def _first_keyword(sql: str) -> Optional[str]:
    text = _remove_sql_comments(sql)
    tokens = re.findall("[a-zA-Z0-9_]+", text)
    for tok in tokens:
        up = tok.upper()
        if re.fullmatch("[A-Z]+", up):
            return up


def _sql_kind(sql: str) -> str:
    first = _first_keyword(sql) or ""
    if first in {"SELECT", "SHOW", "WITH"}:
        return "DQL"
    if first in {"INSERT", "UPDATE", "DELETE"}:
        return "DML"
    return "DDL"


def _ddl_subtype(sql: str) -> str:
    first = _first_keyword(sql) or ""
    if first == "DROP":
        return "DROP"
    if first == "CREATE":
        return "CREATE"
    if first in {"ALTER", "RENAME"}:
        return "ALTER"
    return "OTHER"


def _normalize_obj_type(obj_type: str) -> str:
    t = obj_type.upper()
    if t.startswith("COLUMN"):
        return "COLUMN"
    for key in [
        "TABLE",
        "INDEX",
        "FUNCTION",
        "TRIGGER",
        "VIEW",
        "PROCEDURE",
        "SEQUENCE",
        "DATABASE",
        "SCHEMA",
        "PARTITION",
        "AGGREGATE",
        "ROLE",
        "USER",
    ]:
        if key in t:
            return key
    return t


def _merge_add_metadata(schema: MetadataGraph, to_add: MetadataGraph) -> None:
    for node in to_add.G.nodes:
        schema.add_node_basic(node[0], node[1])
    for parent, child in to_add.G.edges:
        schema.add_edge_basic(parent[1], parent[0], child[1], child[0])


def _apply_del_metadata(schema: MetadataGraph, to_del: MetadataGraph) -> None:
    for name, obj_type in list(to_del.G.nodes):
        if (name, obj_type) in schema.G.nodes:
            schema.G.remove_node((name, obj_type))
        if obj_type in schema._type2names and name in schema._type2names[obj_type]:
            try:
                schema._type2names[obj_type].remove(name)
            except KeyError:
                pass


class NormalizedCaseGenerator:
    def __init__(
        self,
        dbms_cls,
        *,
        random_seed: Optional[int] = None,
        max_retry_per_stmt: int = 100,
        modify_budget: Tuple[int, int] = (2, 6),
        dml_budget: Tuple[int, int] = (2, 8),
        dql_budget: Tuple[int, int] = (2, 8),
        dql_select_current_tables: bool = True,
        dql_select_system_tables: bool = True,
        selection_generator_cls=SQLTrieGenerator,
        blacklist: Optional[List[str]] = None,
    ) -> None:
        self.dbms_cls = dbms_cls
        self.rng = random.Random(random_seed)
        self.max_retry_per_stmt = max_retry_per_stmt
        self.modify_budget = modify_budget
        self.dml_budget = dml_budget
        self.dql_budget = dql_budget
        self._enable_dql_current_tables = dql_select_current_tables
        self._enable_dql_system_tables = dql_select_system_tables
        self._selection_generator_cls = selection_generator_cls
        default_blacklist_map: Dict[str, List[str]] = {
            "mysql": ["SAVEPOINT", "HELP", "IF EXISTS"],
            "mariadb": ["PREPARE", "DEALLOCATE", "SAVEPOINT", "IF EXISTS", "HELP"],
            "tidb": [
                "INFORMATION_SCHEMA.CLUSTER_DEADLOCKS",
                "INFORMATION_SCHEMA.CLUSTER_HARDWARE",
                "INFORMATION_SCHEMA.CLUSTER_LOAD",
                "INFORMATION_SCHEMA.CLUSTER_MEMORY_USAGE",
                "INFORMATION_SCHEMA.CLUSTER_MEMORY_USAGE_OPS_HISTORY",
                "INFORMATION_SCHEMA.CLUSTER_PROCESSLIST",
                "INFORMATION_SCHEMA.CLUSTER_SLOW_QUERY",
                "INFORMATION_SCHEMA.CLUSTER_STATEMENTS_SUMMARY",
                "INFORMATION_SCHEMA.CLUSTER_STATEMENTS_SUMMARY_EVICTED",
                "INFORMATION_SCHEMA.CLUSTER_STATEMENTS_SUMMARY_HISTORY",
                "INFORMATION_SCHEMA.CLUSTER_SYSTEMINFO",
                "INFORMATION_SCHEMA.CLUSTER_TIDB_INDEX_USAGE",
                "INFORMATION_SCHEMA.CLUSTER_TIDB_PLAN_CACHE",
                "INFORMATION_SCHEMA.CLUSTER_TIDB_STATEMENTS_STATS",
                "INFORMATION_SCHEMA.CLUSTER_TIDB_TRX",
                "INFORMATION_SCHEMA.CLUSTER_TRX_SUMMARY",
                "INFORMATION_SCHEMA.INSPECTION_RESULT",
                "INFORMATION_SCHEMA.TIFLASH_REPLICA",
                "sys.schema_unused_indexes",
                "HELP",
                "IF EXISTS",
            ],
            "dameng": ["SAVEPOINT", "DECLARE", "IF EXISTS", "BEGIN"],
            "monetdb": ["SAVEPOINT", "DECLARE", "IF EXISTS"],
            "oceanbase": ["PREPARE", "DEALLOCATE", "SAVEPOINT", "IF EXISTS", "HELP"],
            "starrocks": [
                "PREPARE",
                "DEALLOCATE",
                "SAVEPOINT",
                "information_schema.be_logs",
                "IF EXISTS",
                "HELP",
            ],
        }
        self._dialect_key = dbms_cls.__name__.lower()
        default_bl = (
            default_blacklist_map.get(self._dialect_key.lower(), [])
            if isinstance(self._dialect_key, str)
            else []
        )
        merged_bl = list(
            {*(s.upper() for s in default_bl)}
            | ({*(s.upper() for s in blacklist)} if blacklist else set())
        )
        (self.blacklist): List[str] = merged_bl
        groups: List[
            List[StatementEx]
        ] = dbms_cls.load_validated_corpus_with_metadata_from_file()
        (self.templates): List[StatementEx] = [
            group[-1] for group in groups if not self._is_blacklisted(group[-1].sql)
        ]
        self._build_indexes()
        self._modify_selector = None
        self._dml_selector = None
        self._dql_selector = None
        try:
            if self._selection_generator_cls is not None:
                if self.ddl_modify_pool:
                    self._modify_selector = self._selection_generator_cls(
                        self.ddl_modify_pool, random_seed=random_seed
                    )
                if self.dml_pool:
                    self._dml_selector = self._selection_generator_cls(
                        self.dml_pool, random_seed=random_seed
                    )
                if self.dql_pool:
                    self._dql_selector = self._selection_generator_cls(
                        self.dql_pool, random_seed=random_seed
                    )
        except Exception:
            self._modify_selector = None
            self._dml_selector = None
            self._dql_selector = None
        self._case_counter = 0
        (self.system_tables): List[str] = []
        if self._enable_dql_system_tables:
            try:
                meta_obj = self.dbms_cls.MetaQuery()
                tables = meta_obj.get_systable_names()
                if isinstance(tables, list):
                    seen = set()
                    uniq: List[str] = []
                    for t in tables:
                        if isinstance(t, str) and t not in seen:
                            seen.add(t)
                            uniq.append(t)
                    self.system_tables = uniq
            except Exception:
                self.system_tables = []

    def _build_indexes(self) -> None:
        ddl_pool: List[StatementEx] = []
        dml_pool: List[StatementEx] = []
        dql_pool: List[StatementEx] = []
        for t in self.templates:
            kind = _sql_kind(t.sql)
            if kind == "DDL":
                ddl_pool.append(t)
            elif kind == "DML":
                dml_pool.append(t)
            else:
                dql_pool.append(t)
        (self.ddl_create_by_type): Dict[str, List[StatementEx]] = {}
        (self.ddl_modify_pool): List[StatementEx] = []
        (self.ddl_drop_pool): List[StatementEx] = []
        for t in ddl_pool:
            subtype = _ddl_subtype(t.sql)
            if (
                subtype == "DROP"
                or t.metadata_del
                and t.metadata_del.G.number_of_nodes() > 0
            ):
                self.ddl_drop_pool.append(t)
                continue
            if subtype == "ALTER" or subtype == "OTHER":
                self.ddl_modify_pool.append(t)
            if t.metadata_add and t.metadata_add.G.number_of_nodes() > 0:
                types_added = {
                    _normalize_obj_type(node[1]) for node in t.metadata_add.G.nodes
                }
                for ty in types_added:
                    self.ddl_create_by_type.setdefault(ty, []).append(t)
        self.dml_pool = dml_pool
        self.dql_pool = dql_pool
        (self.all_obj_types_to_cover): List[str] = sorted(
            list(self.ddl_create_by_type.keys()), key=self._type_priority
        )

    @staticmethod
    def _type_priority(obj_type: str) -> int:
        order = {
            "DATABASE": 0,
            "SCHEMA": 1,
            "USER": 1,
            "TABLE": 2,
            "SEQUENCE": 2,
            "FUNCTION": 2,
            "PROCEDURE": 2,
            "ROLE": 3,
            "COLUMN": 3,
            "INDEX": 4,
            "PARTITION": 5,
            "TRIGGER": 5,
            "VIEW": 5,
            "AGGREGATE": 6,
        }
        return order.get(obj_type.upper(), 10)

    def _pick_random(self, items: List[StatementEx]) -> Optional[StatementEx]:
        if not items:
            return
        return self.rng.choice(items)

    def _token_prefix_for_case(self, case_id: int) -> str:
        return f"gn{case_id}t{int(time.time())}g"

    def _try_emit(
        self, template: StatementEx, current_schema: MetadataGraph, token_prefix: str
    ) -> Optional[StatementEx]:
        for _ in range(self.max_retry_per_stmt):
            new_stmt = substitute_statement_by_current_metadata_no_throw(
                template,
                current_schema,
                reserve_token_name=False,
                token_prefix=token_prefix,
            )
            if new_stmt is not None:
                return new_stmt

    def iter_cases(self, num_cases: Optional[int] = None) -> Iterator[List[str]]:
        produced = 0
        while num_cases is None or produced < num_cases:
            self._case_counter += 1
            case_id = self._case_counter
            token_prefix = self._token_prefix_for_case(case_id)
            current_schema = MetadataGraph()
            sqls: List[str] = []
            created_types: List[str] = []
            for obj_type in self.all_obj_types_to_cover * 3:
                candidates = self.ddl_create_by_type.get(obj_type, [])
                attempted = 0
                max_attempt = min(len(candidates), max(1, len(candidates)))
                while attempted < max_attempt:
                    tmpl = self._pick_random(candidates)
                    if tmpl is None:
                        break
                    new_stmt = self._try_emit(tmpl, current_schema, token_prefix)
                    attempted += 1
                    if new_stmt is None:
                        continue
                    if not self._is_blacklisted(new_stmt.sql):
                        sqls.append(new_stmt.sql)
                        _merge_add_metadata(current_schema, new_stmt.metadata_add)
                        created_types.append(obj_type)
                        break
                    else:
                        continue
                    break
            if self.ddl_modify_pool:
                num_modify = self.rng.randint(
                    self.modify_budget[0], self.modify_budget[1]
                )
                for _ in range(num_modify):
                    if self._modify_selector is not None:
                        tmpl = self._modify_selector.generate()
                    else:
                        tmpl = self._pick_random(self.ddl_modify_pool)
                    if tmpl is None:
                        break
                    new_stmt = self._try_emit(tmpl, current_schema, token_prefix)
                    if new_stmt is None:
                        continue
                    if self._is_blacklisted(new_stmt.sql):
                        continue
                    sqls.append(new_stmt.sql)
                    if (
                        new_stmt.metadata_add
                        and new_stmt.metadata_add.G.number_of_nodes() > 0
                    ):
                        _merge_add_metadata(current_schema, new_stmt.metadata_add)
                    if (
                        new_stmt.metadata_del
                        and new_stmt.metadata_del.G.number_of_nodes() > 0
                    ):
                        _apply_del_metadata(current_schema, new_stmt.metadata_del)
            if self.dml_pool:
                num_dml = self.rng.randint(self.dml_budget[0], self.dml_budget[1])
                for _ in range(num_dml):
                    if self._dml_selector is not None:
                        tmpl = self._dml_selector.generate()
                    else:
                        tmpl = self._pick_random(self.dml_pool)
                    if tmpl is None:
                        break
                    new_stmt = self._try_emit(tmpl, current_schema, token_prefix)
                    if new_stmt is None:
                        continue
                    if self._is_blacklisted(new_stmt.sql):
                        continue
                    sqls.append(new_stmt.sql)
                    if (
                        new_stmt.metadata_add
                        and new_stmt.metadata_add.G.number_of_nodes() > 0
                    ):
                        _merge_add_metadata(current_schema, new_stmt.metadata_add)
                    if (
                        new_stmt.metadata_del
                        and new_stmt.metadata_del.G.number_of_nodes() > 0
                    ):
                        _apply_del_metadata(current_schema, new_stmt.metadata_del)
            if (
                self.dql_pool
                or self._enable_dql_current_tables
                or self._enable_dql_system_tables
                and self.system_tables
            ):
                num_dql = self.rng.randint(self.dql_budget[0], self.dql_budget[1])
                current_table_names = []
                if self._enable_dql_current_tables:
                    try:
                        current_table_names = sorted(
                            list(current_schema.get_names_by_type("TABLE"))
                        )
                    except Exception:
                        current_table_names = []
                available_system_tables = []
                if self._enable_dql_system_tables and self.system_tables:
                    available_system_tables = self.system_tables
                for _ in range(num_dql):
                    dql_type_choice = self.rng.choice(
                        ["template", "current_table", "system_table"]
                    )
                    if dql_type_choice == "template" and self.dql_pool:
                        if self._dql_selector is not None:
                            tmpl = self._dql_selector.generate()
                        else:
                            tmpl = self._pick_random(self.dql_pool)
                        if tmpl is None:
                            continue
                        new_stmt = self._try_emit(tmpl, current_schema, token_prefix)
                        if new_stmt is None:
                            continue
                        if self._is_blacklisted(new_stmt.sql):
                            continue
                        sqls.append(new_stmt.sql)
                    elif dql_type_choice == "current_table" and current_table_names:
                        tbl = self.rng.choice(current_table_names)
                        if tbl:
                            candidate = f"SELECT * FROM {tbl}"
                            if not self._is_blacklisted(candidate):
                                sqls.append(candidate)
                    elif dql_type_choice == "system_table" and available_system_tables:
                        full_name = self.rng.choice(available_system_tables)
                        candidate = f"SELECT * FROM {full_name}"
                        if not self._is_blacklisted(candidate):
                            sqls.append(candidate)
            if self.ddl_drop_pool and created_types:
                for obj_type in created_types:
                    drop_candidates = [
                        t
                        for t in self.ddl_drop_pool
                        if t.metadata_del
                        and any(
                            _normalize_obj_type(node[1]) == obj_type
                            for node in t.metadata_del.G.nodes
                        )
                    ]
                    if not drop_candidates:
                        drop_candidates = self.ddl_drop_pool
                    tmpl = self._pick_random(drop_candidates)
                    if tmpl is None:
                        continue
                    new_stmt = self._try_emit(tmpl, current_schema, token_prefix)
                    if new_stmt is None:
                        continue
                    sqls.append(new_stmt.sql)
                    if (
                        new_stmt.metadata_del
                        and new_stmt.metadata_del.G.number_of_nodes() > 0
                    ):
                        _apply_del_metadata(current_schema, new_stmt.metadata_del)
            produced += 1
            yield sqls

    def _is_blacklisted(self, sql_text: str) -> bool:
        try:
            s = (sql_text or "").upper()
            for bad in self.blacklist:
                if bad and bad in s:
                    return True
        except Exception:
            return False
        return False


def create_generator(
    dbms_cls,
    *,
    random_seed: Optional[int] = None,
    max_retry_per_stmt: int = 100,
    modify_budget: Optional[Tuple[int, int]] = None,
    dml_budget: Optional[Tuple[int, int]] = None,
    dql_budget: Optional[Tuple[int, int]] = None,
    selection_generator_cls=SQLTrieGenerator,
) -> NormalizedCaseGenerator:
    dbms_name = dbms_cls.__name__.lower()
    budget_map = {
        "mysql": (100, 100),
        "mariadb": (94, 94),
        "oceanbase": (103, 103),
        "starrocks": (42, 42),
        "tidb": (78, 78),
        "dameng": (84, 84),
        "monetdb": (72, 72),
    }
    default_budget = budget_map.get(dbms_name, (2, 8))
    if modify_budget is None:
        modify_budget = default_budget
    if dml_budget is None:
        dml_budget = default_budget
    if dql_budget is None:
        dql_budget = default_budget
    return NormalizedCaseGenerator(
        dbms_cls,
        random_seed=random_seed,
        max_retry_per_stmt=max_retry_per_stmt,
        modify_budget=modify_budget,
        dml_budget=dml_budget,
        dql_budget=dql_budget,
        selection_generator_cls=selection_generator_cls,
    )


def main(dialect: Optional[str] = None, list_show_before: bool = False) -> None:
    print("================ BEACON initialization start ================")
    import logging
    from pybeacon.test_oracle.runnable_statement_calculator import (
        RunnableStatementCalculator,
    )
    from pybeacon.logging.configure import get_json_and_console_logger
    from pybeacon.dialects.mysql import MySQL
    from pybeacon.dialects.mariadb import MariaDB
    from pybeacon.dialects.tidb import TiDB
    from pybeacon.dialects.starrocks import StarRocks
    from pybeacon.dialects.oceanbase import OceanBase
    from pybeacon.dialects.monetdb import MonetDB
    from pybeacon.dialects.dameng import Dameng

    print("================ BEACON initialization complete ================")
    name_to_cls = {
        "mysql": MySQL,
        "mariadb": MariaDB,
        "tidb": TiDB,
        "starrocks": StarRocks,
        "oceanbase": OceanBase,
        "ob": OceanBase,
        "monetdb": MonetDB,
        "dameng": Dameng,
        "dm": Dameng,
    }
    selected = dialect.lower() if dialect else None
    log_level_name = "INFO"
    if selected is None:
        parser = argparse.ArgumentParser(description="Run tests for a specific DBMS.")
        parser.add_argument(
            "--dbms",
            type=str,
            required=True,
            help="DBMS name (mysql, mariadb, tidb, starrocks, oceanbase, monetdb, dameng)",
        )
        parser.add_argument(
            "--log-level",
            type=str,
            default="INFO",
            choices=["INFO", "ERROR"],
            help="Set log level; default INFO",
        )
        args = parser.parse_args()
        selected = args.dbms.lower()
        list_show_before = False
        log_level_name = args.log_level
    dbms_cls: Type[Dialect] = name_to_cls.get(selected)
    if dbms_cls is None:
        raise ValueError(
            f"Unsupported DBMS: {selected}. Please use one of the following: mysql, mariadb, oceanbase, tidb, starrocks, dameng, monetdb."
        )
    RunnableStatementCalculator.set_default_dbms_cls(dbms_cls)
    RunnableStatementCalculator.enable_catalog_inspector()
    root_user_conf = dbms_cls.DEFAULT_INIT_CONFIG
    json_console_logger = get_json_and_console_logger(
        filename_prefix="generator_normalize_" + root_user_conf["dsn_name"],
        set_as_root=False,
    )
    log_level = getattr(logging, log_level_name)
    try:
        dialect_module = __import__(
            f"pybeacon.dialects.{selected}", fromlist=["console_logger"]
        )
        if hasattr(dialect_module, "console_logger"):
            dialect_module.console_logger._logger.setLevel(log_level)
        mysql_module = __import__(
            f"pybeacon.dialects.mysql", fromlist=["console_logger"]
        )
        if hasattr(mysql_module, "console_logger"):
            mysql_module.console_logger._logger.setLevel(log_level)
    except (ImportError, AttributeError):
        pass
    logging.getLogger("sqlglot").setLevel(logging.CRITICAL + 1)
    print("======= Creating privilege-aware test case generator =======")
    gen = create_generator(dbms_cls, random_seed=7)
    if list_show_before:
        print("======= Listing all valid SHOW statements =======")
        seen = set()
        show_sqls: List[str] = []
        for t in gen.dql_pool:
            sql_text = t.sql
            if isinstance(sql_text, str) and "SHOW" in sql_text.upper():
                normalized = sql_text.strip()
                if any(bad in normalized.upper() for bad in gen.blacklist):
                    continue
                if normalized not in seen:
                    seen.add(normalized)
                    show_sqls.append(normalized)
        for i, s in enumerate(show_sqls, 1):
            print(f"{i:02d}. {s}")
    print("======= Calculating available grant/revoke statements =======")
    from pybeacon.generation.grant_stmt.check_valid import check_valid_grant_stmts
    from pybeacon.generation.grant_stmt.filler import GrantFiller
    from pybeacon.beacon.metadata import StatementEx
    from pybeacon.test_oracle.system_table_inspector import SystemTableInspectorCustom

    available_grant_generator = check_valid_grant_stmts(dbms_cls)
    allow_grant_stmts = []
    allow_grant_stmts.insert(0, StatementEx(""))
    print("======= Starting BAC detection =======")
    init_client: BasicClient = dbms_cls.get_client()
    client = init_client
    root_user_conf = dbms_cls.DEFAULT_INIT_CONFIG
    test_user_conf = dbms_cls.DEFAULT_TEST_CONFIG
    object_filter_regex = "gn[0-9]+t[0-9]+g[0-9]+"
    root_inspector = SystemTableInspectorCustom(
        client,
        metadata_queries=dbms_cls.MetaQuery().get_metaqueries(schema=None),
        client_kwargs=root_user_conf,
        object_name_filter_regex=object_filter_regex,
    )
    test_inspector = SystemTableInspectorCustom(
        client,
        metadata_queries=dbms_cls.MetaQuery().get_metaqueries(schema=None),
        client_kwargs=test_user_conf,
        object_name_filter_regex=object_filter_regex,
    )
    inspector_mode = RunnableStatementCalculator.inspector_mode

    def check_unauthorized_objects(stmt, ret, mode_suffix=""):
        test_inspector.check_statement_change_metadata(stmt)
        root_inspector.check_statement_change_metadata(stmt)
        for mode in inspector_mode:
            illegal_objects = (
                SystemTableInspectorCustom.validate_statement_system_consistency(
                    ret, test_inspector, root_inspector, mode=mode, auto_flush=False
                )
            )
            if illegal_objects:
                json_console_logger.error(
                    "Unauthorized objects found with regular user",
                    l0_mode=mode
                    + mode_suffix
                    + (
                        " (potential false positive because the ALLOWLIST is DISABLED)"
                        if "no_allowlist" in mode
                        else ""
                    ),
                    l1_stmt=stmt,
                    l2_user=test_user_conf["username"],
                    l3_illegal_objects=illegal_objects,
                    l4_result_set=ret,
                )

    gen_iter = gen.iter_cases(None)
    idx = 0
    while True:
        idx += 1
        try:
            case_sqls = next(gen_iter)
        except StopIteration:
            break
        json_console_logger._logger.setLevel(log_level)
        json_console_logger.info("Running SQL corpus", round=idx)
        dbms_cls.reset_client(client)
        for i, s in enumerate(case_sqls, 1):
            s = _remove_sql_comments(s)
            json_console_logger.info(
                "SQL commands with privilege configuration", stmt=s
            )
            ret = client.execute_v2(s, **dbms_cls.DEFAULT_TEST_CONFIG)
            if ret.is_succ() and f"gn{idx}t" in ret.stmt.lower():
                is_dql = _sql_kind(s) == "DQL"
                result = ret.get_result()
                has_rows = isinstance(result, list) and len(result) > 0
                if not is_dql or has_rows:
                    json_console_logger.error(
                        "Unauthorized objects found with regular user",
                        l0_mode="default",
                        l1_stmt=s,
                        l2_user=dbms_cls.DEFAULT_TEST_CONFIG["username"],
                        l4_result_set=result,
                    )
            if ret.is_result_contains_substr(f"gn{idx}t", ignore_case=True):
                result = ret.get_result()
                json_console_logger.error(
                    "Unauthorized objects found with regular user",
                    l0_mode="default",
                    l1_stmt=s,
                    l2_user=dbms_cls.DEFAULT_TEST_CONFIG["username"],
                    l4_result_set=result,
                )
            client.execute_v2(s, **dbms_cls.DEFAULT_ROOT_CONFIG)
        dbms_cls.reset_client(client)
        stmts_with_grant = GrantFiller().fill(
            case_sqls,
            dbms_cls.SQLGLOT_DIALECT,
            available_grant_generator,
            dbms_cls.DEFAULT_TEST_CONFIG["username"],
            dbms_cls.DEFAULT_TEST_CONFIG["database"],
        )
        for i, s in enumerate(stmts_with_grant, 1):
            if "SHOW CREATE" in s.upper():
                continue
            s = _remove_sql_comments(s)
            json_console_logger.info(
                "SQL commands with privilege configuration", stmt=s
            )
            ret = client.execute_v2(s, **test_user_conf)
            root_ret = client.execute_v2(s, **root_user_conf)
            if ret.is_succ() or root_ret.is_succ():
                check_unauthorized_objects(s, ret)
    client.close()


if __name__ == "__main__":
    main()
