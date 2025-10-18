# Scraping Context

The scraping context handles job listing data collection from employer career websites. It provides flexible base classes that support diverse scraping patterns—HTML parsing, pure APIs, and hybrid approaches—while managing state, errors, and database integration.

## Responsibilities

**What scraping context owns:**
- URL discovery and data extraction
- Cache state management (pending/success/failed)
- Status tracking (sets `status='active'` during initial scraping)
- Retry logic and error handling

**What it does NOT do:**
- Database schema management (storage context)
- Job filtering logic (filtering context)


## Scraper Architecture

### Base Class Hierarchy

```
JobListingScraper (Abstract)
    ├── HTMLScraper 
    │     - Two-phase: discover URLs → fetch details
    └── APIScraper
          - Single-phase: complete data in one call
```


**HTMLScraper** - For traditional career sites:
- Separate directory and detail pages
- Requires HTML parsing (BeautifulSoup)

**APIScraper** - For modern API-based interfaces:
- RESTful endpoints returning JSON
- Complete data in paginated batches

## Key Features

- **Resume capability**: Scraping continues from last checkpoint after interruption
- **State tracking**: Every URL has explicit status (pending/success/failed/transient failure)
- **Error handling**: Automatic retries with exponential backoff and circuit breaker
- **Rate limiting**: Configurable delays via YAML (`config/scraping_params.yaml`)
- **Deduplication**: Set-based operations prevent duplicate entries
- **Archive-as-authority**: Database truth overwrites stale cache entries
- **Scraper orchestration**: Automated scraper execution with logging
- **Graceful shutdown**: KeyboardInterrupt (Ctrl+C) saves progress before exiting
- **Centralized HTTP handling**: URLFetcher with transient/permanent failure classification

## Scraper Orchestration

```bash
# Run all scrapers
make scrape

# Run specific scrapers with options
python scripts/run_scrapers.py run ACMEScraper --batch-size 50 --listing-batch-size 100
```

**Features:**
- Timestamped logs in `outs/logs/scraping_*.txt`
- Success/failure tracking with partial progress on errors
- Exit codes for cron/automation (0=success, 1=failures)
- Supports both `__init__` params and `propagate()` params via unified `scraper_kwargs`
- `listing_batch_size` parameter limits listings scraped per iteration (useful for testing/backlog processing)

## Cache State Management

Scrapers track each URL through a **lifecycle** using JSON cache files:

```
TEMP_STATUS ("pending")
    ↓
  scrape attempt
    ↓
SUCCESS_STATUS ("success")  or  FAILURE_STATUS ("failed")  or  TEMP_FAILURE_STATUS (transient, not exported)
```

**TEMP_FAILURE_STATUS**: Transient failures (e.g., 429 Too Many Requests, 503 Service Unavailable) are marked as temporary failures and skipped for the current session. These are never exported to cache and refresh each session, allowing automatic retry on the next run.

### Cache File Format (JSON)

`data/cache/ACME_Corp_listing_urls.json`:
```json
{
  "https://careers.example.com/job/123": {
    "status": "success",
    "last_attempt": "2024-10-14T10:30:00",
    "attempts": 1
  },
  "https://careers.example.com/job/456": {
    "status": "failed",
    "last_attempt": "2024-10-14T10:31:00",
    "attempts": 3,
    "error": "HTTPError: 404"
  },
  "https://careers.example.com/job/789": {
    "status": "pending",
    "last_attempt": null,
    "attempts": 0
  }
}
```


### Resume Capability

When scraper restarts:
1. Loads cache from JSON file
2. Loads archived URLs from database
3. Merges: database truth overwrites stale cache entries
4. Continues scraping only pending/failed URLs


## Two-Phase Scraping (HTMLScraper)

Most career sites use this pattern:

**Phase 1: URL Discovery**
```python
scrape_urls_by_directory_page(page) -> list[str]
```
- Fetch directory/search page
- Extract job listing URLs
- Add to cache with `TEMP_STATUS`

**Phase 2: Detail Fetching**
```python
parse_listing_webpage(url, html_response) -> dict
```
- Fetch individual listing page
- Extract details (title, description, salary, etc.)
- Set `Status='active'`, `Last Checked=now()`
- Write to database

**Why two phases?**
- Efficiently discover all listings first
- Selectively fetch only unarchived details
- Resume mid-scrape without re-discovering URLs

## HTTP Request Handling

### URLFetcher (`requests.py`)

Centralized HTTP handling with intelligent failure classification:

**Failure Classification:**
- **Permanent failures**: 401, 403, 404, 410, invalid URLs, redirect loops → marked as "failed"
- **Transient failures**: 408, 429, 500-504, timeouts → marked as "transient failure"
- **Circuit breaker**: Stops scraping after consecutive transient failures to respect rate limits

**Usage:**
```python
from scout.contexts.scraping.requests import URLFetcher

fetcher = URLFetcher(max_consecutive_transient_failures=5)
response = fetcher.fetch(url)
# Returns None on transient failure, response object on success
```

### Rate Limiting Configuration

Request timing parameters are configured via YAML (`config/scraping_params.yaml`):
```yaml
timing:
  request_delay: 1.0    # Seconds between individual requests
  batch_delay: 2.0      # Seconds between batches
  max_retries: 2        # Maximum retry attempts
```

This centralizes timing configuration, making it easy to adjust rate limiting without changing code.

## Graceful Shutdown

Scrapers handle KeyboardInterrupt (Ctrl+C) gracefully:
- Exports cache immediately to preserve progress
- Completes current batch before exiting
- Allows incremental backlog processing

**Example workflow:**
```bash
# Start scraping large backlog
python scripts/run_scrapers.py run ACMEScraper

# Press Ctrl+C after partial progress
^C  # Cache saved automatically

# Resume later - picks up where it left off
python scripts/run_scrapers.py run ACMEScraper
```


