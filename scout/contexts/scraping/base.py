"""
Base classes for job listing scrapers.

This module defines the abstract base classes and common functionality for all job scrapers:
- JobListingScraper: Abstract base with orchestration, caching, and database operations
- HTMLScraper: For sites requiring HTML parsing (two-phase: ID discovery → detail fetching)
- APIScraper: For API-based sites (single-phase: complete data in one call)
"""

import os
import json
import time
import requests
from datetime import datetime

import pandas as pd
from tqdm import tqdm
from dataclasses import dataclass
from abc import ABC, abstractmethod
from sqlalchemy import create_engine
from typing import List, Dict, Tuple

from scout.contexts.storage import (
    get_database_wrapper,
    DatabaseConfig,
)


def html_request_with_retry(url, method="GET", max_attempts=3, delay=1.0, **kwargs):
    """
    Make an HTTP request with automatic retry on failure.

    Args:
        url (str): The URL to request
        method (str): HTTP method - either 'GET' or 'POST' (default: 'GET')
        max_attempts (int): How many times to try the request (default: 3)
        delay (float): Initial delay in seconds between retries (default: 1.0)
        **kwargs: Any additional arguments to pass to requests.get() or requests.post()

    Returns:
        requests.Response: The response object from successful request

    Raises:
        requests.RequestException: If all retry attempts fail
    """
    most_recent_exception = None

    for attempt in range(max_attempts):
        try:
            if method == "GET":
                response = requests.get(url, **kwargs)
                response.raise_for_status()
                return response
            elif method == "POST":
                response = requests.post(url, **kwargs)
                response.raise_for_status()
                return response

        except requests.RequestException as e:
            most_recent_exception = e

            if attempt < max_attempts - 1:
                # Exponential backoff: delay * (2^attempt)
                wait_time = delay * (2**attempt)
                print(f"Request failed, retrying in {wait_time}s...")
                time.sleep(wait_time)

    raise most_recent_exception


class JobListingScraper(ABC):
    """
    Abstract base class for all job listing scrapers.

    Provides common functionality:
    - Database operations (read/write to database)
    - Cache management (URL/ID persistence)
    - Progress tracking (failed IDs, completed status)
    - Orchestration (batch processing, retry logic)
    """

    def __init__(
        self,
        df2db_col_map,
        cache_path=None,
        database_name=None,
        id_column_name="url",
        request_delay=1.0,
        batch_delay=2.0,
        max_retries=2,
        db_config=None,
    ):
        self.db_config = db_config or DatabaseConfig.from_env(name=database_name)

        assert cache_path is not None, "Cache path not provided."

        # Ensure cache uses .json extension
        assert cache_path.endswith('.json')
        self.cache_path = cache_path

        self.batch_delay = batch_delay
        self.max_retries = max_retries
        self.request_delay = request_delay
        self.id_col_name = id_column_name
        self.id_scraping_completed = False

        self.failed_ids = []
        self.all_cached_ids = []
        self.cache_data = {}  # Stores status info for each URL

        # Load cache (creates from database if missing)
        self.import_ids_from_cache()

        self.fields = list(df2db_col_map.keys())
        self.df2db_col_map = df2db_col_map
        self.db2df_col_map = {v: k for k, v in df2db_col_map.items()}

        assert self.id_col_name in self.db2df_col_map.keys(), (
            "The id we are use to track scraping progress (usually 'url') must be a column of the database"
        )

        self.listing_scraping_completed = False

        self.attach_db()

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

    def keep_id_list_updated(self, id_list):
        """Add new IDs to cached list (deduplication via set logic)."""
        new_ids = set(id_list) - set(self.all_cached_ids)
        self.all_cached_ids.extend(new_ids)

    def _cache_from_archive(self):
        archived_urls = self.load_archived_ids()
        
        
        cache_data = { url: {
                "status": "success",
                "last_attempt": None,
                "attempts": 1
                } for url in archived_urls }
        return cache_data

    def import_ids_from_cache(self):
        """Load IDs from JSON cache file with status tracking."""
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r") as f:
                try:
                    self.cache_data = json.load(f)
                    # Extract all URLs regardless of status
                    cached_ids = list(self.cache_data.keys())
                    self.keep_id_list_updated(cached_ids)
                    return
                except json.JSONDecodeError:
                    print(f"Cache file corrupted, refreshing cache from archive.")

        self.cache_data = self._cache_from_archive()
        cached_ids = list(self.cache_data.keys())
        self.keep_id_list_updated(cached_ids)

    def export_ids_to_cache(self):
        """Write all cached IDs to JSON cache file with status."""
        with open(self.cache_path, "w") as f:
            json.dump(self.cache_data, f, indent=2)

    def load_archived_ids(self):
        """Load IDs already saved to database."""
        try:
            archived_ids = self.db.get_column_values(
                column_name=self.id_col_name, table_name=self.db_config.table
            )
        except Exception as e:
            print(
                f"Error while attempting to load listings archive:\n{e}\n\nNo listings can be detected. Starting over from scratch."
            )
            archived_ids = []

        print(f"Archived listings so far: {len(archived_ids)}")
        self.keep_id_list_updated(archived_ids)
        return archived_ids

    def determine_ids_to_archive(self, candidate_ids: list, retry_failures: bool = False) -> list:
        """
        Get IDs that haven't been archived yet (excluding failed IDs unless retry_failures=True).

        Args:
            candidate_ids: List of IDs to consider
            retry_failures: If True, include previously failed IDs; if False, skip them

        Returns:
            List of IDs to scrape
        """
        archived_ids = set(self.load_archived_ids())

        # Filter out previously failed IDs unless retrying
        if retry_failures:
             return list(set(candidate_ids) - archived_ids)
        else:
            failed_ids = [
                url for url, data in self.cache_data.items()
                if data["status"] == "failed"
            ]
            return list(set(candidate_ids) - archived_ids - set(self.failed_ids))

    @abstractmethod
    def fetch_next_batch(self, batch_size: int, retry_failures: bool) -> tuple[list, pd.DataFrame]:
        """
        Fetch next batch of listings.

        Returns: (list of IDs, DataFrame of listings to archive)
        """
        pass

    def propagate(self, batch_size: int = 10, retry_failures: bool = False) -> pd.DataFrame:
        """
        Common orchestration logic for all scrapers.
        Fetches batches until all listings are scraped.

        Args:
            batch_size: Number of listings to scrape per batch
            retry_failures: If True, retry previously failed URLs; if False, skip them
        """
        while not self.listing_scraping_completed:
            # Fetch next batch
            scraped_ids, listing_batch_df = self.fetch_next_batch(batch_size, retry_failures=retry_failures)

            # Update cache with new IDs
            if scraped_ids:
                self.keep_id_list_updated(scraped_ids)
                self.export_ids_to_cache()

            # Archive new listings
            if len(listing_batch_df) > 0:
                self.append_df_to_db(listing_batch_df)

            # Check if we're done
            if not scraped_ids:
                archived_ids = set(self.load_archived_ids())
                if set(archived_ids) | set(self.failed_ids) == set(self.all_cached_ids):
                    self.listing_scraping_completed = True
                    break

            # Be polite to the server
            time.sleep(self.batch_delay)


class HTMLScraper(JobListingScraper):
    """
    Base class for websites requiring HTML parsing.

    Uses two-phase approach:
    1. Directory scan: Paginate through listing pages to discover job IDs/URLs
    2. Detail fetch: Retrieve and parse individual job pages
    """

    def __init__(
        self,
        df2db_col_map,
        cache_path=None,
        database_name=None,
        current_directory_page=0,
    ):
        self.current_directory_page = current_directory_page

        super().__init__(
            df2db_col_map=df2db_col_map,
            cache_path=cache_path,
            database_name=database_name,
        )

    @abstractmethod
    def scrape_ids_by_directory_page(self, page) -> list:
        """Fetch job IDs/URLs from a single directory page."""
        pass

    @abstractmethod
    def parse_listing_webpage(self, url, html_response) -> dict:
        """Extract job details from individual job page."""
        pass

    def scrape_next_listing_batch(self, ids) -> pd.DataFrame:
        """Fetch and parse multiple job listing pages."""
        scraped_info_list = []

        for listing_id in tqdm(ids):
            try:
                fetched_listing_webpage = html_request_with_retry(
                    url=listing_id,
                    delay=self.request_delay,
                    max_attempts=self.max_retries,
                )
                assert fetched_listing_webpage.url == listing_id, (
                    f"{listing_id} redirected to {fetched_listing_webpage.url} likely because the listing is no longer available"
                )

                scraped_info = self.parse_listing_webpage(
                    url=listing_id, html_response=fetched_listing_webpage
                )
                scraped_info_list.append(scraped_info)

                # Mark as successful in cache
                self.cache_data[listing_id] = {
                    "status": "success",
                    "last_attempt": datetime.now().isoformat(),
                    "attempts": self.cache_data.get(listing_id, {}).get("attempts", 0) + 1
                }

                time.sleep(self.request_delay)

            except Exception as e:
                print(
                    f"Failed to scrape {listing_id} after {self.max_retries} attempts: {e}"
                )
                self.failed_ids.append(listing_id)

                # Mark as failed in cache
                self.cache_data[listing_id] = {
                    "status": "failed",
                    "last_attempt": datetime.now().isoformat(),
                    "attempts": self.cache_data.get(listing_id, {}).get("attempts", 0) + 1,
                    "error": str(e)
                }
                self.export_ids_to_cache()  # Persist immediately

        if self.failed_ids:
            print(f"Failed to scrape {len(self.failed_ids)} listings")

        if len(scraped_info_list):
            return self.postprocess_df(pd.DataFrame(scraped_info_list))
        else:
            return pd.DataFrame()

    def scrape_next_id_batch(self, pages_per_batch: int) -> list:
        """Scrape IDs from multiple directory pages."""
        assert pages_per_batch > 0, (
            "Wot in tarnation! Your pages_per_batch is not a positive number!"
        )

        page = self.current_directory_page
        page_end = page + pages_per_batch

        scraped_ids = []
        while True:
            if page >= page_end:
                break

            page_i_ids = self.scrape_ids_by_directory_page(page)
            n_ids_added = len(page_i_ids)
            print(f"Found {n_ids_added} jobs on page {page}.")
            if not n_ids_added:
                self.id_scraping_completed = True
                break

            scraped_ids += page_i_ids
            page += 1
            time.sleep(self.request_delay)

        if pages_per_batch > 1:
            print(f"--------------------\nListing id count: {len(scraped_ids)}")
        self.current_directory_page = page
        return scraped_ids

    def fetch_next_batch(self, batch_size: int, retry_failures: bool = False) -> tuple[list, pd.DataFrame]:
        """
        Implementation of abstract method for HTML scraping.
        Two-phase: first get IDs, then fetch details for unarchived ones.
        """

        # Phase 1: Get new IDs if we haven't finished scanning directory
        if not self.id_scraping_completed:
            new_ids = self.scrape_next_id_batch(pages_per_batch=batch_size)
        else:
            new_ids = []

        # Phase 2: Get unarchived IDs and fetch their details
        ids_of_listings_to_fetch = self.determine_ids_to_archive(
            self.all_cached_ids,
            retry_failures=retry_failures
        )

        if ids_of_listings_to_fetch:
            listings_df = self.scrape_next_listing_batch(ids_of_listings_to_fetch)
        else:
            listings_df = pd.DataFrame()

        print(f"Fetched {len(new_ids)} new IDs, {len(listings_df)} listings to archive")
        return new_ids, listings_df


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

    def fetch_next_batch(self, batch_size: int, retry_failures:bool = False) -> tuple[list, pd.DataFrame]:
        """
        Implementation of abstract method for API scraping.
        Single-phase: API returns full listing data in one call.
        """
        listing_index = self.batch_current * batch_size

        try:
            # Fetch data from API with retry
            fetched_data = self.fetch_next_listing_batch(
                listing_index=listing_index, n_listings=batch_size
            )

            # Parse the response
            fetched_ids, fetched_listings_df = self.parse_api_response(fetched_data)

            if not len(fetched_ids):
                return [], pd.DataFrame()

            # Filter to only unarchived listings
            unarchived_ids = self.determine_ids_to_archive(
                fetched_ids,
                retry_failures=retry_failures
            )
            to_archive_mask = fetched_listings_df[self.id_col_name].isin(unarchived_ids)
            listings_to_archive_df = fetched_listings_df[to_archive_mask]

            print(
                f"Fetched {len(fetched_ids)} listings, {len(listings_to_archive_df)} to archive"
            )

            self.batch_current += 1
            return fetched_ids, self.postprocess_df(listings_to_archive_df)

        except Exception as e:
            print(f"Failed to fetch batch at index {listing_index}: {e}")
            self.batch_current += 1
            return [], pd.DataFrame()
