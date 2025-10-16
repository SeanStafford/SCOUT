"""
Job scraping domain.

Handles discovery and extraction of job listings from various career websites.
"""

from scout.contexts.scraping.base import (
    JobListingScraper,
    HTMLScraper,
    APIScraper,
    html_request_with_retry,
)
from scout.contexts.scraping.orchestration import (
    run_scraper,
    run_scrapers,
)

__all__ = [
    "JobListingScraper",
    "HTMLScraper",
    "APIScraper",
    "html_request_with_retry",
    "run_scraper",
    "run_scrapers",
]
