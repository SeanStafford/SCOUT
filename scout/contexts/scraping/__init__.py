"""
Job scraping domain.

Handles discovery and extraction of job listings from various career websites.
"""

from scout.contexts.scraping.base import (
    JobListingScraper,
    HTMLScraper,
    APIScraper,
    ListingDatabaseConfig,
    html_request_with_retry,
)

__all__ = [
    "JobListingScraper",
    "HTMLScraper",
    "APIScraper",
    "ListingDatabaseConfig",
    "html_request_with_retry",
]
