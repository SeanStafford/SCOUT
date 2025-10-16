"""Minimal event logger for schema migrations written to JSON Lines."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
LOGS_PATH = Path(os.getenv("LOGS_PATH", "outs/logs"))


def log_schema_migration_event(
    database: str,
    table: str,
    column: str,
    datatype: str,
    action: str,
    reason: str,
    rows_affected: Optional[int] = None,
    log_dir: Path = LOGS_PATH,
) -> None:
    """Append a schema-change event to ``schema_migrations.txt`` in JSON Lines."""

    log_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(),
        "database": database,
        "table": table,
        "column": column,
        "datatype": datatype,
        "action": action,
        "reason": reason,
        "rows_affected": rows_affected,
    }

    # Keep one JSON object per line so downstream tools can stream the file.
    with open(log_dir / "schema_migrations.txt", "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
