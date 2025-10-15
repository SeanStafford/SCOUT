"""
Storage maintenance workers for processing events from other contexts.

Inspired by the broadcast-subscribe pattern. This acts like the consumer side.
Reads event logs and updates database accordingly.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

from scout.contexts.storage.database import DatabaseWrapper

load_dotenv()
LOGS_PATH = Path(os.getenv("LOGS_PATH", "outs/logs"))


def process_inactive_events(
    db_wrapper: DatabaseWrapper,
    table: str = "listings",
    log_dir: Path = LOGS_PATH,
    verbose: bool = True
) -> int:
    """
    Process listing_became_inactive events and update database.

    This implements the consumer side of the broadcast-subscribe pattern.
    The storage context reads events produced by the filtering context
    and updates the database (which storage context owns).

    Args:
        db_wrapper: DatabaseWrapper instance
        table: Table name to update (default: "listings")
        log_dir: Directory containing log files (default: LOGS_PATH from environment)
        verbose: Print progress information (default: True)

    Returns:
        Number of events processed

    Process:
        1. Read unprocessed events from listing_became_inactive.txt
        2. For each event, UPDATE database with new status and timestamp
        3. Move processed events to listing_became_inactive_processed.txt (archive)
        4. Remove from active log

    Example:
        from scout.contexts.storage import get_database_wrapper, DatabaseConfig
        from scout.contexts.storage.maintenance import process_inactive_events

        config = DatabaseConfig.from_env('booz_job_listings')
        db = get_database_wrapper(config)
        events_processed = process_inactive_events(db)
        print(f"Processed {events_processed} events")
    """
    log_path = Path(log_dir)
    active_log = log_path / "listing_became_inactive.txt"
    archive_log = log_path / "listing_became_inactive_processed.txt"

    # Check if active log exists
    if not active_log.exists():
        if verbose:
            print(f"No active event log found at {active_log} .")
        return 0

    # Read all events from active log
    with open(active_log, "r") as f:
        lines = f.readlines()

    if not lines:
        if verbose:
            print("No events to process.")
        return 0

    events = []
    malformed_lines = []
    for line in lines:
        try:
            event = json.loads(line.strip())
            events.append(event)
        except json.JSONDecodeError as e:
            if verbose:
                print(f"Skipping malformed event: {line.strip()} (error: {e})")
            malformed_lines.append(line)

    if not events:
        if verbose:
            print("No valid events found")
        return 0

    if verbose:
        print(f"Processing {len(events)} events...")

    # Update database
    conn = db_wrapper.connect() # a session with the database
    cursor = conn.cursor() # allows execution of SQL commands and retrieval of results

    # Begin transaction
    try:
        events_processed = 0
        for event in events:
            url = event["url"]
            new_status = event["new_status"]
            timestamp = event["timestamp"]

            # %s placeholders prevent SQL injection by safely escaping user values
            cursor.execute(
                f"UPDATE {table} SET status = %s, last_checked = %s WHERE url = %s",
                (new_status, timestamp, url)
            )

            events_processed += 1

        # Make all changes to the database permenant at once updates above are applied together.
        # If an error occurs before this during the transaction, no events are are updated.
        conn.commit()

        if verbose:
            print(f"Successfully updated {events_processed} rows in database")

    except Exception as e:
        # If an error occurs during the transaction, this reverts all updates.
        conn.rollback()
        if verbose:
            print(f"Error during database UPDATE: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    # Archive processed events
    try:
        # Append successfully processed events to archive
        with open(archive_log, "a") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Rewrite active log with only malformed events (preserves unprocessable data for manual review)
        with open(active_log, "w") as f:
            f.writelines(malformed_lines)

        if verbose:
            print(f"Archived {len(events)} events to {archive_log}")
            if malformed_lines:
                print(f"Retained {len(malformed_lines)} malformed events in active log for review")

    except Exception as e:
        if verbose:
            print(f"Warning: Events processed but archival failed: {e}")
        # Worst case: events remain in active log and get reprocessed (idempotent updates)

    return events_processed
