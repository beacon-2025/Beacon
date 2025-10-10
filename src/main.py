import sys
sys.modules["main"] = sys.modules[__name__]

import _import_hook
import mysql_client
import dameng_client
import mariadb_client
import monetdb_client
import oceanbase_client
import starrocks_client
import tidb_client
import postgres_client
import generator
import validator
import argparse, importlib, sys
from datetime import datetime
from pathlib import Path


def _load_accio_module():
    try:
        return importlib.import_module("run.accio_reproduce_poc")
    except Exception:
        return importlib.import_module("accio")


def _resolve_poc_dir(dbms_name: str) -> Path:
    normalized = dbms_name.lower()
    base_dir = Path(__file__).resolve().parent
    if normalized == "oceanbase":
        poc_dir = base_dir / "corpus" / "pysqlsmith" / "mysql"
    else:
        poc_dir = base_dir / "corpus" / "pysqlsmith" / normalized
    return poc_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Accio")
    parser.add_argument(
        "--dbms",
        required=True,
        help="DBMS name (e.g. mysql, tidb, clickhouse, oracle, mariadb, firebird, oceanbase)",
    )
    args = parser.parse_args()
    dbms_name = args.dbms.lower()
    poc_dir = _resolve_poc_dir(dbms_name)
    base_dir = Path(__file__).resolve().parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    log_path = logs_dir / f"accio_{dbms_name}_{timestamp}.log"
    result_path = logs_dir / f"accio_{dbms_name}_{timestamp}.result"
    accio = _load_accio_module()
    argv = [
        "accio_reproduce_poc",
        "--dbms",
        dbms_name,
        "--poc",
        str(poc_dir),
        "--json",
        "--log-file",
        str(log_path),
        "--out",
        str(result_path),
        "--poc-workers",
        "1",
        "--instance",
        "1",
    ]
    original_argv = sys.argv
    try:
        sys.argv = argv
        accio.main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main()
