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
- **State tracking**: Every URL has explicit status (pending/success/failed)
- **Error handling**: Automatic retries with exponential backoff
- **Rate limiting**: Configurable delays between requests
- **Deduplication**: Set-based operations prevent duplicate entries
- **Archive-as-authority**: Database truth overwrites stale cache entries


## Cache State Management

Scrapers track each URL through a **lifecycle** using JSON cache files:

```
TEMP_STATUS ("pending")
    ↓
  scrape attempt
    ↓
SUCCESS_STATUS ("success")  or  FAILURE_STATUS ("failed")
```

### Cache File Format (JSON Lines)

`data/cache/booz_listing_urls.json`:
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

