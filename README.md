# SCOUT
```
   ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
   █                                                                       █
   █                                 ██████                                █
   █                            ████████████████                           █
   █                           █████▀▀▀   ▀▀█████                          █
   █                          ██▀ ▓▓▓▓▓▓▓▓▓▓▓▓ ▀██                         █
   █                          ▀█▓▓▓▓▓▓▓▓▓       █                          █
   █                           █                █                          █
   █                   ▄▄ ▄██████████▄ ▄▄ ▄██████████▄▄                    █
   █                 █▀ █▀▀▀  ▀▀██████▓▒▒▓██████▀▀  ▀▀▀█ ▀▄                █
   █                █  █  ▒▒▒▒▒▒ ██████████████ ▒▒▒▒▒▒  █  █               █
   █                █ ▄▀ ▒▒▒▒▒▒▒▒ █████▀ ▀████ ▒▒▒▒▒▒▒▒ █▄ █               █
   █                █ ▀▄ ▒▒▒▒▒▒▒▒ ███▀    ▀███ ▒▒▒▒▒▒▒▒ ██ █               █
   █               █▀  █▄ ▒▒▒▒▒▒ ██▀        ▀██ ▒▒▒▒▒▒ ██  ▀█              █
   █               █    ▀█▄▄▄▄▄▄█              ██▄▄▄▄▄█▀     █             █
   █             ██▄        ▄█  █              █  █▄        ▄██            █
   █            ██████▄  ▄▄▀    ██            ██    ▀▄▄  ▄██████           █
   █           ██████████▄       ██          ██        ██████████          █
   █          ████████████       █ ▀▀▀▀▀▀▀▀▀▀ █       ████████████         █
   █         ████████████     ▄███            ███▄     ████████████        █
   █        ████████████▀  ▄███████▄        ▄██████▄   ▀████████████       █
   █       ██████████████████████████▄    ▄██████████████████████████      █
   █     ██████████████████████████████▒▒█████████████████████████████     █
   █     ██████████████████████████████▒▒█████████████████████████████     █
   █     ██████████████████████████████▒▒█████████████████████████████     █
   █      █████████████████████████████▒▒████████████████████████████      █
   █                                                                       █
   █   ██████████   ██████████   ███████████   ██       ██   ███████████   █
   █   ██           ███          ██       ██   ██       ██       ███       █
   █   ██           ███          ██       ██   ██       ██       ███       █
   █   ██████████   ███          ██       ██   ██       ██       ███       █
   █           ██   ███          ██       ██   ██       ██       ███       █
   █           ██   ███          ██       ██   ██       ██       ███       █
   █   ██████████   ██████████   ███████████   ███████████       ███       █
   █                                                                       █
   █    Scraping Career Opportunities Using Technology                     █
   █                                                              v0.1.0   █
   █                                            created by Sean Stafford   █
   █                                                                       █
   ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
```


**Scraping Career Opportunities Using Technology**

A domain-driven job scraping and filtering system. SCOUT scrapes job listings from employer career sites, stores them in PostgreSQL, and provides flexible filtering through declarative configuration files.

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL (with a running instance)
- Make (for using Makefile commands)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd SCOUT

# Create virtual environment
make venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
make install

# For development (includes pytest, ruff, jupyter)
# make install-dev

# Configure database (optional)
# Copy .env.example to .env and customize
cp .env.example .env

# IMPORTANT: Set proper permissions on .env to protect credentials
chmod 600 .env

# Edit .env to set your PostgreSQL password and other settings
```

## Architecture

SCOUT follows Domain-Driven Design with three main bounded contexts:

### 1. Scraping Context
Handles data collection from career websites. Supports both HTML parsing and API-based scrapers.

- **Cache management**: Tracks scraped/failed/pending URLs with JSON state files
- **Status tracking**: Marks listings as `active` during initial scraping
- **Resume capability**: Interrupted scrapes continue from last checkpoint

### 2. Storage Context
Manages database operations and schema. Database-agnostic design with PostgreSQL implementation.

- **Event consumer**: Processes status change events from filtering context
- **Maintenance workers**: Updates database based on event logs
- **Schema utilities**: Inspect and visualize database structure

### 3. Filtering Context
Job filtering through YAML configuration files ("declarative")

- **FilterPipeline**: Config-driven filtering (SQL + pandas operations)
- **Event producer**: Logs status changes when URLs become inactive
- **Read-only**: Never directly modifies database (respects bounded contexts)

---

### Project Structure

```
SCOUT/
├── scout/
│   ├── contexts/
│   │   ├── scraping/       # Data collection (HTMLScraper, APIScraper)
│   │   ├── storage/        # Database operations
│   │   └── filtering/      # Config-driven filtering
│   └── utils/              # Shared utilities (text processing, etc.)
├── config/                 # Filtering configuration
├── data/
│   ├── cache/              # URL cache files (JSON)
│   └── exports/
├── outs/
│   └── logs/               # Event logs for cross-context communication
├── notebooks/
├── tests/                  # Test suite
│   ├── unit/
│   └── integration/
└── docs/                   # Documentation
```

---

### Scraper Types

**1. JobListingScraper (Abstract Base)**
- Common orchestration, caching, and database operations
- Progress tracking and batch processing
- Retry logic and error handling

**2. HTMLScraper**
- For websites requiring HTML parsing
- Two-phase: ID discovery → detail fetching

**3. APIScraper**
- For pure API-based job sites
- Single-phase: complete data in one call

---

### Communication without (direct) coupling

Contexts communicate through **log files** rather than direct calls, maintaining loose coupling:

```
Filtering Context                Storage Context
    (producer)                      (consumer)
        │                               │
        │  check_active()               │
        │  detects inactive URL         │
        │                               │
        ├──> Event Log ──────────────>  │
        │    (JSON file)                │  process_inactive_events()
        │                               │  updates database
        │                               ▼
```

This pattern respects **bounded context** principles: each context owns its domain, communicating via events instead of direct database access.

---


## Example Workflow

**1. Configure Filters** (`config/filters.yaml`)

**2. Run Scraper**
```python
from scout.contexts.scraping.scrapers import BoozScraper

scraper = BoozScraper()
scraper.propagate(batch_size=50)
```

**3. Apply Filters** (notebook)
```python
from scout.contexts.filtering import FilterPipeline

pipeline = FilterPipeline("config/filters.yaml")
query = pipeline.build_sql_query()
df = scraper.import_db_as_df(query=query)
df_filtered = pipeline.apply_filters(df)
```

**4. Process Events** (maintenance)
```python
from scout.contexts.storage import process_inactive_events

events_processed = process_inactive_events(db)
```

---
## Key Features

- **Flexible Architecture**: Base classes handle common functionality while supporting diverse scraping patterns
- **Resume Capability**: Cache files and database state tracking allow interrupted scrapes to continue
- **Error Handling**: Automatic retry logic with exponential backoff and failed ID tracking
- **Deduplication**: Set-based operations prevent duplicate entries
- **Rate Limiting**: Configurable delays to avoid bot detection
- **Two-Phase Pattern**: Efficient ID discovery followed by selective detail fetching



## Technical Details

### Database Schema

Each employer has its own database with a `listings` table. Column names are mapped via `df2db_col_map` in each scraper.

Common fields:
- `title`: Job title
- `description`: Job description (markdown format)
- `location`: Job location(s)
- `remote`: Remote work status
- `date_posted`: Posting date
- `url`: Job listing URL (used as unique identifier)

### Caching Strategy

- **Cache Files**: Store all discovered job IDs/URLs (`data/cache/*.txt`)
- **Database**: Store complete job details
- **Resume Logic**: On restart, scraper checks both cache and database to determine what's already been processed
- **Failed IDs**: Tracked separately to avoid infinite retry loops

### Rate Limiting

- `request_delay`: Delay between individual requests (default: 1.0s)
- `batch_delay`: Delay between batches (default: 2.0s)
- `max_retries`: Maximum retry attempts (default: 2)


## Useful commands for development

```bash
# View all available commands
make help

# Format code before committing
make format

# Check code quality
make lint

# Clean cache files
make clean

# View cache statistics
make cache-stats

# Log cache stats to timestamped file
make cache-log

```

## Roadmap

### Near Term
- Unified database schema across all employers
- Metadata table to track scraping history
- Smarter wait times (randomized delays)

### Medium Term
- CLI interface for easier operation
- Proxy pool for higher throughput
- Background service for automated scraping
- Job filtering framework with configurable criteria

### Long Term
- Neo4J integration for graph-based analysis
- Automated job feed curation
- REST API for external access