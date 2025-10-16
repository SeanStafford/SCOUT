"""
Storage maintenance workers for processing events from other contexts.

Inspired by the broadcast-subscribe pattern. This acts like the consumer side.
Reads event logs and updates database accordingly.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

from scout.contexts.storage.database import DatabaseWrapper, DatabaseConfig
from scout.contexts.storage.getter import get_database_wrapper

load_dotenv()
LOGS_PATH = Path(os.getenv("LOGS_PATH", "outs/logs"))


def process_status_events_for_database(
    db_wrapper: DatabaseWrapper,
    table: str = "listings",
    log_dir: Path = LOGS_PATH,
    verbose: bool = True
) -> int:
    """
    Process status change events for a specific database.

    This implements the consumer side of the broadcast-subscribe pattern.
    The storage context reads events produced by the filtering context
    and updates the database (which storage context owns).

    Args:
        db_wrapper: DatabaseWrapper instance for the target database
        table: Table name to update (default: "listings")
        log_dir: Directory containing log files (default: LOGS_PATH from environment)
        verbose: Print progress information (default: True)

    Returns:
        Number of events processed

    Process:
        1. Read unprocessed events from listing_status_changed.txt
        2. Filter to only events for this database
        3. For each event, UPDATE database with new status and timestamp
        4. Move processed events to listing_status_changed_processed.txt (archive)
        5. Remove processed events from active log
    """
    log_path = Path(log_dir)
    active_log = log_path / "listing_status_changed.txt"
    archive_log = log_path / "listing_status_changed_processed.txt"

    database_name = db_wrapper.config.name

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

    # Parse and filter events
    all_events = [] # TODO: Should implement a more efficient way of handling multi-database event processing than reading every event for every database
    events_for_this_db = []
    malformed_lines = []

    for line in lines:
        try:
            event = json.loads(line.strip())
            all_events.append((line, event))

            # Filter to only this database
            if event["database"] == database_name:
                events_for_this_db.append(event)

        except json.JSONDecodeError as e:
            if verbose:
                print(f"Skipping malformed event: {line.strip()} (error: {e})")
            malformed_lines.append(line)

    if not events_for_this_db:
        if verbose:
            print(f"No events found for '{database_name}' database")
        return 0

    if verbose:
        print(f"Processing {len(events_for_this_db)} events for '{database_name}' database...")

    # Update database
    conn = db_wrapper.connect() # a session with the database
    cursor = conn.cursor() # allows execution of SQL commands and retrieval of results

    # Begin transaction
    try:
        events_processed = 0
        for event in events_for_this_db:
            url = event["url"]
            new_status = event["new_status"]
            timestamp = event["timestamp"]

            # %s placeholders prevent SQL injection
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

    # Archive processed events and update active log
    try:
        # Append processed events to archive
        with open(archive_log, "a") as f:
            for event in events_for_this_db:
                f.write(json.dumps(event) + "\n")

        # Rewrite active log with:
        # - Events for other databases (not processed)
        # - Malformed events (also not processed, for manual review)
        events_to_keep = [
            raw_line for raw_line, event in all_events
            if event.get("database") != database_name
        ]

        with open(active_log, "w") as f:
            f.writelines(events_to_keep + malformed_lines)

        if verbose:
            print(f"Archived {len(events_for_this_db)} events to {archive_log}")
            if malformed_lines:
                print(f"Retained {len(malformed_lines)} malformed events in active log for review")
            other_db_count = len(events_to_keep)
            if verbose and other_db_count:
                print(f"Retained {other_db_count} events for other databases in active log")

    except Exception as e:
        if verbose:
            print(f"Warning: Events processed but archival failed: {e}")

    return events_processed


def process_status_events(
    database_names: str | list[str] | None = None,
    table: str = "listings",
    log_dir: Path = LOGS_PATH,
    verbose: bool = True
) -> dict[str, int]:
    """
    Orchestrator: process status events for one or more databases.

    Creates DatabaseWrapper objects internally -> Suitable for standalone execution (cron jobs, maintenance scripts).

    Args:
        database_names: Database name(s) to process
                       - str: single database
                       - list[str]: multiple databases
                       - None: discover all databases from events
        table: Table name (default: "listings")
        log_dir: Event log directory (default: LOGS_PATH)
        verbose: Print progress (default: True)

    Returns:
        Dict mapping database_name → events_processed

    Example:
        # Process all databases found in events
        process_status_events()
        # OR 
        # Process just specified databases
        process_status_events(["ACME_Corp_job_listings", "MomCorp_job_listings"])
    """

    # Convert to list regardless of provided type
    if database_names is None:
        database_names = _discover_databases_from_events(log_dir)
        if verbose and database_names:
            print(f"Discovered databases: {', '.join(database_names)}")
    elif isinstance(database_names, str):
        database_names = [database_names]

    if not database_names:
        if verbose:
            print("No databases to process")
        return {}

    results = {}
    for db_name in database_names:
        if verbose:
            print(f"\n--- Processing database: {db_name} ---")

        # Create DatabaseWrapper for this database
        db_config = DatabaseConfig.from_env(name=db_name)
        db_wrapper = get_database_wrapper(db_config)

        # Process events for this database
        count = process_status_events_for_database(
            db_wrapper=db_wrapper,
            table=table,
            log_dir=log_dir,
            verbose=verbose
        )
        results[db_name] = count

    return results


def _discover_databases_from_events(log_dir: Path) -> list[str]:
    """Helper: discover unique database names from event log."""
    log_file = log_dir / "listing_status_changed.txt"
    if not log_file.exists():
        return []

    databases_with_events = set()
    with open(log_file, "r") as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                if "database" in event: # checks that 'database' key exists in event
                    databases_with_events.add(event["database"])
            except json.JSONDecodeError:
                continue

    return sorted(databases_with_events)
