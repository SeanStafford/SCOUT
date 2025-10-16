#!/usr/bin/env python3
"""
Command-line interface for running job scrapers.

Uses typer for clean CLI with subcommands.
"""

import sys
from pathlib import Path
from typing import List, Optional

import typer

# Add project root to path so we can import scout
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scout.contexts.scraping.orchestration import _get_available_scrapers, run_scrapers

app = typer.Typer(
    add_completion=False,
    help="SCOUT job scraper orchestration",
)


@app.command("run")
def run_command(
    scrapers: Optional[List[str]] = typer.Argument(
        None,
        help="Scraper(s) to run (e.g., MomCorpScraper). If none specified, runs all scrapers.",
    ),
    batch_size: int = typer.Option(
        10,
        "--batch-size",
        "-b",
        help="Number of items to process per batch",
        min=1,
    ),
    retry_failures: bool = typer.Option(
        False,
        "--retry-failures",
        "-r",
        help="Retry previously failed URLs",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress verbose output (errors still logged)",
    ),
    start_page: Optional[int] = typer.Option(
        None,
        "--start-page",
        "-p",
        help="Starting directory page number (default: 0)",
        min=0,
    ),
):
    """
    Run job scrapers with logging to timestamped files.

    By default, runs all available scrapers. Specify scraper names to run only those.

    Examples:

        # Run all scrapers
        $ run_scrapers.py run

        # Run specific scrapers
        $ run_scrapers.py run MomCorpScraper ACMEScraper

        # Custom batch size and retry failures
        $ run_scrapers.py run --batch-size 100 --retry-failures

        # Run specific scraper with options
        $ run_scrapers.py run MomCorpScraper -b 5 -r

        # Start from a specific page (useful for testing)
        $ run_scrapers.py run MomCorpScraper --start-page 30
    """
    # None or empty list -> run all scrapers
    scraper_names = scrapers if scrapers else None

    # Validate scraper names if provided
    if scrapers:
        available = set(_get_available_scrapers())
        invalid = [s for s in scrapers if s not in available]
        if invalid:
            typer.secho(
                f"Error: Unknown scraper(s): {', '.join(invalid)}",
                fg=typer.colors.RED,
                err=True,
            )
            typer.echo(f"\nAvailable scrapers: {', '.join(sorted(available))}", err=True)
            typer.echo("\nUse 'list' command to see all available scrapers", err=True)
            raise typer.Exit(code=1)

    # Build scraper kwargs if start_page specified
    scraper_kwargs = None
    if start_page is not None:
        scraper_kwargs = {"current_directory_page": start_page}

    # Run scrapers
    try:
        results = run_scrapers(
            scraper_names=scraper_names,
            batch_size=batch_size,
            retry_failures=retry_failures,
            verbose=not quiet,
            scraper_kwargs=scraper_kwargs,
        )

        # Exit with error code if any scrapers failed
        failures = sum(1 for r in results.values() if r["status"] == "failed")
        if failures > 0:
            raise typer.Exit(code=1)

    except KeyboardInterrupt:
        typer.secho("\n\nInterrupted by user", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=130)


@app.command("list")
def list_command():
    """List all available scrapers."""
    available = _get_available_scrapers()
    typer.secho(f"Available scrapers ({len(available)}):", fg=typer.colors.BLUE, bold=True)
    for scraper in available:
        typer.echo(f"  • {scraper}")


if __name__ == "__main__":
    app()
