"""
Base classes for job listing scrapers.

This module defines the abstract base classes and common functionality for all job scrapers:
- JobListingScraper: Abstract base with orchestration, caching, and database operations
- HTMLScraper: For sites requiring HTML parsing (two-phase: URL discovery → detail fetching)
- APIScraper: For API-based sites (single-phase: complete data in one call)
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from dataclasses import dataclass
from abc import ABC, abstractmethod
from sqlalchemy import create_engine
from typing import List, Dict, Tuple
from omegaconf import OmegaConf
from dotenv import load_dotenv

from scout.contexts.storage import (
    get_database_wrapper,
    DatabaseConfig,
)

load_dotenv()
CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "config"))

# Cache status constants defining the URL lifecycle:
# TEMP_STATUS: URL discovered but not yet scraped
# SUCCESS_STATUS: Successfully fetched and archived to database
# FAILURE_STATUS: Failed after all retry attempts (permanent)
# TEMP_FAILURE_STATUS: Failed this session (transient), don't retry until next session
SUCCESS_STATUS = "success"
FAILURE_STATUS = "failed"
TEMP_STATUS = "pending"
TEMP_FAILURE_STATUS = "temp_failure"

from scout.contexts.scraping.requests import (
    URLFetcher,
    NetworkCircuitBreakerException,
    LINK_GOOD,
    LINK_BAD,
    LINK_UNKNOWN,
)


class JobListingScraper(ABC):
    """
    Abstract base class for all job listing scrapers.

    Provides common functionality:
    - Database operations (read/write to database)
    - Cache management
    - Progress tracking
    - Orchestration (batch processing, retry logic)
    """

    def __init__(
        self,
        df2db_col_map,
        cache_path=None,
        database_name=None,
        url_column_name="url",
        fetch_config=None,
        db_config=None,
    ):
        self.db_config = db_config or DatabaseConfig.from_env(name=database_name)

        # Load fetch config (use provided config or default from file)
        if fetch_config is None:
            fetch_config = OmegaConf.load(CONFIG_PATH / "fetch.yaml")
        self.fetch_config = fetch_config

        self.url_col_name = url_column_name
        self.url_scraping_completed = False
        self.listing_scraping_completed = False

        self.fetcher = URLFetcher(
            max_consecutive_failures=self.fetch_config.max_consecutive_failures,
            request_delay=self.fetch_config.request_delay,
            max_retries=self.fetch_config.max_retries,
        )

        self.fields = list(df2db_col_map.keys())
        self.df2db_col_map = df2db_col_map
        self.db2df_col_map = {v: k for k, v in df2db_col_map.items()}

        assert self.url_col_name in self.db2df_col_map.keys(), (
            "The id we are use to track scraping progress (assumed to be 'url') must be a column of the database"
        )

        self.attach_db()
        self._load_cache(cache_path)


    def attach_db(self):
        """Attach to database, creating if necessary."""
        self.db = get_database_wrapper(self.db_config, ensure_exists=True)

    def append_df_to_db(self, df):
        """Append DataFrame to database table."""
        df_with_db_col_names = df.rename(columns=self.df2db_col_map)

        postgres_engine = create_engine(self.db_config.connection_string)

        df_with_db_col_names.to_sql(
            self.db_config.table, postgres_engine, if_exists="append", index=False
        )

    def import_db_as_df(self, query=None):
        """Load database table as DataFrame with original column names."""
        query = query if query is not None else f"SELECT * from {self.db_config.table}"
        df = self.db.export_df(query)
        return df.rename(columns=self.db2df_col_map)

    def postprocess_df(self, df):
        """
        Override in subclasses for custom DataFrame processing.

        Example: date parsing, type conversion, column remapping.
        """
        return df

    def _update_cache(self, new_data, data_directly_from_cache_file=False):
        """
        Merge new status data into cache and mark for export.

        The cache_is_updated flag enables lazy cache export - we only write to disk
        when necessary, not after every status change.
        """
        assert isinstance(new_data, dict), "New data must be a dict mapping URLs to status info"
        self.cache.update(new_data)
        if new_data and not data_directly_from_cache_file:
            self.cache_is_updated = True

    def _cache_from_archive(self):
        """
        Build cache from database URLs, marking all as SUCCESS_STATUS.

        This establishes archive as the source of truth - if it's in the database,
        it was successfully scraped regardless of what the cache file says.
        """
        archived_urls = self.get_archived_urls()

        cache = { url: {
                "status": SUCCESS_STATUS,
                "last_attempt": None,
                "attempts": 1
                } for url in archived_urls }
        return cache
    
    def _load_cache(self, cache_path):
        assert cache_path is not None, "Cache path not provided."
        self.cache_path = cache_path

        self.cache = {}  # Stores status info for each URL
        self.cache_is_updated = False

        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                try:
                    self._update_cache(json.load(f), data_directly_from_cache_file=True)
                except json.JSONDecodeError:
                    print(f"Could not import cache from {cache_path} due to JSONDecodeError, refreshing cache from archive.")
        else:
            print(f"{cache_path} does not exist, inferring cache from archive.")
        
        cache_inferred_from_archive = self._cache_from_archive()

        # Merge archive truth with cached failures/pending:
        # - If URL is in archive, mark as SUCCESS (overrides stale failed/pending)
        # - If URL is in cache but not archive, preserve its status (failed/pending)
        self._update_cache({ url: data for url, data in cache_inferred_from_archive.items() if not (url in self.cache.keys() and self.cache[url]["status"] == SUCCESS_STATUS) })     

    def _export_cache(self):
        """
        Write complete cache to JSON cache file with status.

        Converts TEMP_FAILURE_STATUS to TEMP_STATUS on export so transient
        failures are retried in next session.
        """
        cache_to_export = {}
        for url, data in self.cache.items():
            if data["status"] == TEMP_FAILURE_STATUS:
                cache_to_export[url] = {**data, "status": TEMP_STATUS}
            else:
                cache_to_export[url] = data

        with open(self.cache_path, "w") as f:
            json.dump(cache_to_export, f, indent=2)
        self.cache_is_updated = False
    
    def print_cache_summary(self):
        statuses = [SUCCESS_STATUS, FAILURE_STATUS, TEMP_STATUS]
        status_counts = {status: 0 for status in statuses}
        for data in self.cache.values():
            status_counts[data["status"]] += 1
        print(" | ".join([f"{status}: {count}" for status, count in status_counts.items()]))

    def get_archived_urls(self):
        """Get list of URLS already successfully archived to database."""
        try:
            archived_urls = self.db.get_column_values(
                column_name=self.url_col_name, table_name=self.db_config.table
            )
        except Exception as e:
            print(
                f"Error while attempting to load listings archive:\n{e}\n\nNo listings can be detected. Starting over from scratch."
            )
            archived_urls = []

        return archived_urls

    def _filter_cached_urls_by_status(self, statuses: list[str] | str) -> list[str]:
        """
        Filter cached URLs by status.
        """
        if isinstance(statuses, str):
            statuses = [statuses]

        return [url for url, data in self.cache.items() if data["status"] in statuses]

    def _pick_urls_to_archive(self, new_urls: list, retry_failures: bool = False) -> list:
        """
        Determine which URLs should be scraped in this batch.

        Assigns TEMP_STATUS to newly discovered URLs (eager status assignment).
        Returns all TEMP_STATUS URLs, plus FAILURE_STATUS if retry_failures=True.
        Excludes TEMP_FAILURE_STATUS (already tried this session).
        This ensures every URL has a status before scraping attempts.
        """
        # Assign pending status to new URLs
        self._update_cache({ url: {
                "status": TEMP_STATUS,
                "last_attempt": None,
                "attempts": 0
                } for url in new_urls if url not in self.cache.keys() })

        # Build list of statuses to fetch
        STATUS_LIST_TO_FETCH = [TEMP_STATUS]
        if retry_failures:
            STATUS_LIST_TO_FETCH.append(FAILURE_STATUS)
        # Note: TEMP_FAILURE_STATUS is intentionally excluded (don't retry this session)

        return self._filter_cached_urls_by_status(STATUS_LIST_TO_FETCH)

    @abstractmethod
    def fetch_next_batch(self, batch_size: int, retry_failures: bool, listing_batch_size: int = None) -> tuple[list, pd.DataFrame]:
        """
        Fetch next batch of listings.

        Args:
            batch_size: Number of directory pages to process
            retry_failures: Whether to retry failed URLs
            listing_batch_size: Max listings to scrape per iteration

        Returns: (list of URLs, DataFrame of listings to archive)
        """
        pass

    def propagate(self, batch_size: int = 10, retry_failures: bool = False, listing_batch_size: int = None) -> pd.DataFrame:
        """
        Common orchestration logic for all scrapers.
        Fetches batches until all listings are scraped.

        Args:
            batch_size: Number of directory pages to scrape per batch
            retry_failures: If True, retry previously failed URLs; if False, skip them
            listing_batch_size: Max number of detail listings to scrape per iteration (default: all pending)
        """
        try:
            while not self.listing_scraping_completed:
                # Fetch next batch
                scraped_urls, listing_batch_df = self.fetch_next_batch(
                    batch_size,
                    retry_failures=retry_failures,
                    listing_batch_size=listing_batch_size
                )

                # Archive new listings
                if len(listing_batch_df) > 0:
                    self.append_df_to_db(listing_batch_df)

                # Lazy export: only write to disk when cache has changed
                if self.cache_is_updated:
                    self._export_cache()

                # Check if we're done: completion when no pending URLs remain
                # (success + failed URLs are terminal states)
                if not scraped_urls:
                    pending_urls = self._filter_cached_urls_by_status(TEMP_STATUS)

                    if not pending_urls:
                        self.listing_scraping_completed = True
                        break

                # Be polite to the server
                time.sleep(self.fetch_config.batch_delay)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user - saving progress...")
            if self.cache_is_updated:
                self._export_cache()
                print(f"✓ Cache exported to {self.cache_path}")
            raise  # Re-raise so orchestration layer can handle cleanup


class HTMLScraper(JobListingScraper):
    """
    Base class for websites requiring HTML parsing.

    Uses two-phase approach:
    1. Directory scan: Paginate through listing pages to discover job URLs
    2. Detail fetch: Retrieve and parse individual job pages
    """

    def __init__(
        self,
        df2db_col_map,
        cache_path=None,
        database_name=None,
        current_directory_page=0,
        fetch_config=None,
    ):
        self.current_directory_page = current_directory_page

        super().__init__(
            df2db_col_map=df2db_col_map,
            cache_path=cache_path,
            database_name=database_name,
            fetch_config=fetch_config,
        )

    @abstractmethod
    def scrape_urls_by_directory_page(self, page) -> list:
        """
        Fetch job URLs from a single directory page.

        Implementations should use self.fetcher.fetch() for HTTP requests
        to enable circuit breaking and consistent error handling.
        """
        pass

    @abstractmethod
    def parse_listing_webpage(self, url, html_response) -> dict:
        """Extract job details from individual job page."""
        pass

    def scrape_next_listing_batch(self, urls) -> pd.DataFrame:
        """Fetch and parse multiple job listing pages."""
        temp_cache = {}
        scraped_info_list = []

        try:
            for listing_url in tqdm(urls):
                response, classification, error_msg = self.fetcher.fetch(listing_url)

                if classification == LINK_GOOD:
                    scraped_info = self.parse_listing_webpage(
                        url=listing_url, html_response=response
                    )

                    # Set initial status and timestamp (if columns exist in df2db_col_map)
                    scraped_info["Status"] = "active"
                    scraped_info["Last Checked"] = datetime.now()

                    scraped_info_list.append(scraped_info)

                    # Mark as successful in cache
                    temp_cache[listing_url] = {
                        "status": SUCCESS_STATUS,
                        "last_attempt": datetime.now().isoformat(),
                        "attempts": self.cache[listing_url]["attempts"] + 1
                    }

                elif classification == LINK_BAD:
                    print(
                        f"Permanent failure for {listing_url}: {error_msg or 'Unknown error'}"
                    )
                    temp_cache[listing_url] = {
                        "status": FAILURE_STATUS,
                        "last_attempt": datetime.now().isoformat(),
                        "attempts": self.cache[listing_url]["attempts"] + 1,
                        "error": error_msg or "Permanent failure"
                    }

                else:  # LINK_UNKNOWN (transient failure)
                    print(f"Transient failure for {listing_url}: {error_msg or 'Unknown error'}")
                    temp_cache[listing_url] = {
                        "status": TEMP_FAILURE_STATUS,
                        "last_attempt": datetime.now().isoformat(),
                        "attempts": self.cache[listing_url]["attempts"] + 1,
                        "error": error_msg or "Transient failure"
                    }

                time.sleep(self.fetch_config.request_delay)

        except KeyboardInterrupt:
            # Save partial progress before re-raising
            if temp_cache:
                self._update_cache(temp_cache)
            raise  # Re-raise to bubble up

        # Batch update cache after all scraping attempts (reduces I/O)
        self._update_cache(temp_cache)

        if len(scraped_info_list):
            return self.postprocess_df(pd.DataFrame(scraped_info_list))
        else:
            return pd.DataFrame()

    def scrape_next_url_batch(self, pages_per_batch: int) -> list:
        """Scrape URLs from multiple directory pages."""
        assert pages_per_batch > 0, (
            "Wot in tarnation! Your pages_per_batch is not a positive number!"
        )

        page_start = self.current_directory_page
        page_end = page_start + pages_per_batch

        scraped_urls = []
        print("Jobs found by directory page: ", end="")
        for page in range(page_start, page_end):
            page_i_urls = self.scrape_urls_by_directory_page(page)
            n_urls_added = len(page_i_urls)
            if page > page_start:
                print(" "*30, end="")
            print(f"{n_urls_added:-3} on page {page:-3}\n", end="")
            # Empty page indicates end of directory listing
            if not n_urls_added:
                self.url_scraping_completed = True
                break
            scraped_urls += page_i_urls
            time.sleep(self.fetch_config.request_delay)

        self.current_directory_page = page + 1
        return scraped_urls

    def fetch_next_batch(self, batch_size: int, retry_failures: bool = False, listing_batch_size: int = None) -> tuple[list, pd.DataFrame]:
        """
        Implementation of abstract method for HTML scraping.
        Two-phase: first get URLs, then fetch details for unarchived ones.

        If there are pending listings and listing_batch_size is set,
        Phase 1 (directory scraping) is skipped to finish pending work first.
        """


        # Phase 1: Get new URLs (skip if we have more pendings than listing_batch_size)
        new_urls = []
        pending_urls = self._filter_cached_urls_by_status(TEMP_STATUS)

        if self.url_scraping_completed:
            pass
        else:
            # Check if there are pending listings (not yet attempted this session)
            if listing_batch_size is None or len(pending_urls) < listing_batch_size:
                new_urls = self.scrape_next_url_batch(pages_per_batch=batch_size)
            else:
                print(f"Skipping directory scan - {len(pending_urls)} pending listings to process first")

        # Phase 2: Get unarchived URLs and fetch their details
        urls_of_listings_to_fetch = self._pick_urls_to_archive(
            new_urls,
            retry_failures=retry_failures
        )

        # Limit to listing_batch_size if specified
        if listing_batch_size and len(urls_of_listings_to_fetch) > listing_batch_size:
            urls_of_listings_to_fetch = urls_of_listings_to_fetch[:listing_batch_size]
            print(f"Limiting batch to {listing_batch_size} listings (out of {len(pending_urls)} pending)")

        if not self.url_scraping_completed and new_urls:
            batch_summary_printout = " "*30 + "-"*20 + "\n" + " "*30
            batch_summary_printout += f"{len(new_urls):-3} total | {len(urls_of_listings_to_fetch):-3} to fetch"
            print(batch_summary_printout)
        elif self.url_scraping_completed and not pending_urls:
            print(f"✓ Directory scan complete.")

        # Export cache now if new URLs were assigned pending status
        if self.cache_is_updated:
            self._export_cache()

        if urls_of_listings_to_fetch:
            listings_df = self.scrape_next_listing_batch(urls_of_listings_to_fetch)
        else:
            listings_df = pd.DataFrame()

        print(f"{len(urls_of_listings_to_fetch)} attempted fetches | {len(listings_df)} successful fetches | {len(urls_of_listings_to_fetch) - len(listings_df)} failed fetches")
        return new_urls, listings_df


class APIScraper(JobListingScraper):
    """
    Base class for API-based job sites.

    Uses single-phase approach: API typically returns complete job data in one call.
    """

    def __init__(
        self,
        df2db_col_map,
        cache_path=None,
        database_name=None,
        base_url=None,
    ):
        self.base_url = base_url
        self.batch_current = 0

        super().__init__(
            df2db_col_map=df2db_col_map,
            cache_path=cache_path,
            database_name=database_name,
        )

    @abstractmethod
    def parse_api_response(self, response_data) -> Tuple[list, List[Dict]]:
        """Parse API response into job records."""
        pass

    @abstractmethod
    def fetch_next_listing_batch(self, listing_index, n_listings):
        """Fetch a batch of listings from the API."""
        pass

    def fetch_next_batch(self, batch_size: int, retry_failures: bool = False, listing_batch_size: int = None) -> tuple[list, pd.DataFrame]:
        """
        Implementation of abstract method for API scraping.
        Single-phase: API returns full listing data in one call.
        """
        listing_index = self.batch_current * batch_size

        try:
            fetched_data = self.fetch_next_listing_batch(
                listing_index=listing_index, n_listings=batch_size
            )

            # Initialize before parsing (needed for exception handler scope)
            fetched_urls = []
            fetched_urls, fetched_listings_df = self.parse_api_response(fetched_data)

        except Exception as e:
            print(f"Failed to fetch batch at index {listing_index}: {e}")

            # Mark URLs as failed if parse succeeded but something else failed
            # (won't have URLs if fetch/parse failed before URL extraction)
            if fetched_urls:
                temp_cache = {
                    url: {
                        "status": FAILURE_STATUS,
                        "last_attempt": datetime.now().isoformat(),
                        "attempts": self.cache.get(url, {}).get("attempts", 0) + 1,
                        "error": str(e)
                    }
                    for url in fetched_urls if url in self.cache
                }
                self._update_cache(temp_cache)

            self.batch_current += 1
            return [], pd.DataFrame()
        
        if not len(fetched_urls):
            return [], pd.DataFrame()

        # Filter to only unarchived listings
        unarchived_urls = self._pick_urls_to_archive(
            fetched_urls,
            retry_failures=retry_failures
        )
        to_archive_mask = fetched_listings_df[self.url_col_name].isin(unarchived_urls)
        listings_to_archive_df = fetched_listings_df[to_archive_mask]

        # Mark successfully fetched URLs as success
        temp_cache = {
            url: {
                "status": SUCCESS_STATUS,
                "last_attempt": datetime.now().isoformat(),
                "attempts": self.cache[url]["attempts"] + 1
            }
            for url in unarchived_urls
        }
        self._update_cache(temp_cache)

        print(
            f"Fetched {len(fetched_urls)} listings, {len(listings_to_archive_df)} to archive"
        )

        self.batch_current += 1
        return fetched_urls, self.postprocess_df(listings_to_archive_df)

