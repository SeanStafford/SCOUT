import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
LOGS_PATH = Path(os.getenv("LOGS_PATH", "outs/logs"))


def log_schema_migration_event(database, table, column, datatype, action, reason, rows_affected = None, log_dir= LOGS_PATH):
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
    with open(log_dir / "schema_migrations.txt", "a") as handle:
        handle.write(json.dumps(payload) + "\n")
