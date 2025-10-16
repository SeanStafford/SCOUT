"""
Scraper orchestration for running multiple scrapers with logging.

Provides functionality to:
- Run all scrapers or a specified list
- Log execution details to timestamped files
- Track successes and failures
- Return structured results

Similar pattern to storage context's process_status_events().
"""

import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger

# Import scraper registry
from scout.contexts.scraping.scrapers import __all__ as AVAILABLE_SCRAPERS

load_dotenv()
LOGS_PATH = Path(os.getenv("LOGS_PATH", "outs/logs"))


def _setup_logger(log_dir: Path = LOGS_PATH) -> Path:
    """
    Configure loguru to write to timestamped log file.

    Args:
        log_dir: Directory for log files (default: LOGS_PATH from environment)

    Returns:
        Path to the created log file
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"scraping_{timestamp}.txt"

    # Remove default handler and add file handler
    logger.remove()  # Remove default stderr handler
    logger.add(log_file, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    logger.add(
        lambda msg: print(msg, end=""),  # Also print to console
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}\n",
        level="INFO",
    )

    return log_file


def _get_available_scrapers() -> list[str]:
    """
    Get list of available scraper class names.

    Returns:
        List of scraper class names from scrapers/__init__.py __all__
    """
    return AVAILABLE_SCRAPERS


def _import_scraper_class(scraper_name: str) -> type:
    """
    Dynamically import a scraper class by name.

    Args:
        scraper_name: Name of scraper class (e.g., "MomCorpScraper")

    Returns:
        Scraper class

    Raises:
        ImportError: If scraper cannot be imported
    """
    from scout.contexts.scraping import scrapers

    try:
        scraper_class = getattr(scrapers, scraper_name)
        return scraper_class
    except AttributeError:
        raise ImportError(f"Scraper '{scraper_name}' not found in scrapers module")


def run_scraper(
    scraper_name: str,
    batch_size: int = 50,
    retry_failures: bool = False,
    verbose: bool = True,
    scraper_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run a single scraper and return results.

    Args:
        scraper_name: Name of scraper class (e.g., "MomCorpScraper")
        batch_size: Number of items per batch for propagate()
        retry_failures: Whether to retry previously failed URLs
        verbose: Print progress information
        scraper_kwargs: Additional keyword arguments to pass to scraper constructor
                       (e.g., {"current_directory_page": 67})

    Returns:
        Dict with keys:
            - status: "success" or "failed"
            - rows_added: Number of rows added (if successful)
            - time_elapsed: Time in seconds
            - database_name: Database name (if successful)
            - error: Error message (if failed)
            - traceback: Full traceback (if failed)
    """
    start_time = time.time()
    result = {
        "status": "failed",
        "rows_added": 0,
        "time_elapsed": 0.0,
        "database_name": None,
        "error": None,
        "traceback": None,
    }

    initial_rows = 0
    scraper = None

    try:
        logger.info(
            f"[{scraper_name}] Starting (batch_size={batch_size}, retry_failures={retry_failures})"
        )

        # Import and instantiate scraper
        scraper_class = _import_scraper_class(scraper_name)
        kwargs = scraper_kwargs or {}
        scraper = scraper_class(**kwargs)

        # Get initial row count
        initial_df = scraper.import_db_as_df()
        initial_rows = len(initial_df)

        # Run scraper (may return None or DataFrame)
        scraper.propagate(batch_size=batch_size, retry_failures=retry_failures)

        # Get final row count from database
        final_df = scraper.import_db_as_df()
        final_rows = len(final_df)
        rows_added = final_rows - initial_rows
        elapsed = time.time() - start_time

        result.update(
            {
                "status": "success",
                "rows_added": rows_added,
                "time_elapsed": elapsed,
                "database_name": scraper.db_config.name,
            }
        )

        logger.success(
            f"[{scraper_name}] Completed: {rows_added} rows added to {scraper.db_config.name} ({elapsed:.1f}s)"
        )

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        error_traceback = traceback.format_exc()

        # Try to calculate partial progress even on failure
        rows_added_partial = 0
        database_name = None

        if scraper:  # Scraper was successfully instantiated
            try:
                database_name = scraper.db_config.name
                current_df = scraper.import_db_as_df()
                rows_added_partial = len(current_df) - initial_rows
            except Exception:
                # If we can't get current state, leave as 0
                pass

        result.update(
            {
                "status": "failed",
                "rows_added": rows_added_partial,
                "time_elapsed": elapsed,
                "database_name": database_name,
                "error": error_msg,
                "traceback": error_traceback,
            }
        )

        # Log with partial progress info if available
        if rows_added_partial > 0:
            logger.error(
                f"[{scraper_name}] Failed after adding {rows_added_partial} rows: {error_msg} ({elapsed:.1f}s)"
            )
        else:
            logger.error(f"[{scraper_name}] Failed: {error_msg} ({elapsed:.1f}s)")

        if verbose:
            logger.debug(f"[{scraper_name}] Traceback:\n{error_traceback}")

    return result


def run_scrapers(
    scraper_names: str | list[str] | None = None,
    batch_size: int = 50,
    retry_failures: bool = False,
    verbose: bool = True,
    log_dir: Path = LOGS_PATH,
    scraper_kwargs: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Orchestrator: run one or more scrapers with detailed logging.

    Args:
        scraper_names: Scraper name(s) to run
                      - str: single scraper (e.g., "MomCorpScraper")
                      - list[str]: multiple scrapers
                      - None: run all available scrapers
        batch_size: Number of items per batch for propagate() (default: 50)
        retry_failures: Whether to retry previously failed URLs (default: False)
        verbose: Print progress information (default: True)
        log_dir: Directory for log files (default: LOGS_PATH)
        scraper_kwargs: Additional keyword arguments to pass to scraper constructor
                       (e.g., {"current_directory_page": 67})

    Returns:
        Dict mapping scraper_name → result dict with keys:
            - status: "success" or "failed"
            - rows_added: Number of rows added
            - time_elapsed: Time in seconds
            - database_name: Database name (if successful)
            - error: Error message (if failed)

    Example:
        # Run all scrapers
        results = run_scrapers()

        # Run specific scrapers
        results = run_scrapers(["MomCorpScraper", "ACMEScraper"], batch_size=100)

        # Run single scraper starting from page 67
        results = run_scrapers("MomCorpScraper", scraper_kwargs={"current_directory_page": 67})
    """
    # Setup logging
    log_file = _setup_logger(log_dir)
    logger.info(f"Logging to: {log_file}")

    # Convert to list regardless of provided type
    if scraper_names is None:
        scraper_names = _get_available_scrapers()
        if verbose:
            logger.info(f"Auto-discovered {len(scraper_names)} scrapers")
    elif isinstance(scraper_names, str):
        scraper_names = [scraper_names]

    if not scraper_names:
        logger.warning("No scrapers to run")
        return {}

    logger.info(f"Starting scraper orchestration")
    logger.info(f"Running {len(scraper_names)} scraper(s): {', '.join(scraper_names)}")

    # Run each scraper
    results = {}
    successes = 0
    failures = 0

    for scraper_name in scraper_names:
        result = run_scraper(
            scraper_name=scraper_name,
            batch_size=batch_size,
            retry_failures=retry_failures,
            verbose=verbose,
            scraper_kwargs=scraper_kwargs,
        )
        results[scraper_name] = result

        if result["status"] == "success":
            successes += 1
        else:
            failures += 1

    # Summary
    logger.info(
        f"Orchestration complete: {successes}/{len(scraper_names)} scrapers succeeded, {failures} failed"
    )

    if verbose and successes > 0:
        total_rows = sum(r["rows_added"] for r in results.values() if r["status"] == "success")
        total_time = sum(r["time_elapsed"] for r in results.values())
        logger.info(f"Total: {total_rows} rows added across all scrapers ({total_time:.1f}s)")

    return results
