"""
Event logging for cross-context communication.

Implements broadcast-subscribe pattern via log files.
Filtering context produces events, storage context consumes them.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
LOGS_PATH = Path(os.getenv("LOGS_PATH", "outs/logs"))


def log_inactive_event(url: str, old_status: str, new_status: str, log_dir: Path = LOGS_PATH) -> None:
    """
    Log an event when a listing becomes inactive.

    Inspired by the broadcast-subscribe pattern. This acts like the producer side.
    The filtering context can log events but it cannot update the database directly.
    The storage context will handle these events with its maintenance.py

    Args:
        url: Unique identifier for the listing
        old_status: Previous status
        new_status: New status
        log_dir: Directory for log files (default: LOGS_PATH from environment)
    """
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Construct event
    # Status options: 'active', 'inactive', 'unknown'
    event = {
        "timestamp": datetime.now().isoformat(),
        "url": url,
        "old_status": old_status,
        "new_status": new_status,
    }

    # Append to log file
    # Using JSON Lines format with one JSON object per line
    log_file = log_path / "listing_became_inactive.txt"

    with open(log_file, "a") as f:
        f.write(json.dumps(event) + "\n")
