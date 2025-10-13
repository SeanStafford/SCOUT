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

A job listing scraper system that collects job postings from various employers and stores them in PostgreSQL for analysis and filtering. SCOUT provides a flexible, extensible framework for scraping job listings from multiple career websites. It handles diverse website patterns—traditional HTML, pure APIs, and hybrid approaches—through a domain-driven architecture that makes it easy to add new job sites.

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

SCOUT follows Domain-Driven Design (DDD) principles with clear separation of concerns:


### Project Structure


```
SCOUT/
├── scout/                  
│   ├── contexts/           # Domain contexts
│   │   ├── scraping/       
│   │   └── storage/        
│   └── utils/              
├── data/                  
│   ├── cache/              # URL cache files
│   └── exports/           
├── notebooks/            
├── outs/                 
│   └── logs/             
├── tests/                  # Test suite
│   ├── unit/
│   └── integration/
└── docs/                   # Documentation
```


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


## Development Workflow

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
- Enhanced error handling for failed listings

### Medium Term
- CLI interface for easier operation
- Proxy pool for higher throughput
- Background service for automated scraping
- Job filtering framework with configurable criteria

### Long Term
- Neo4J integration for graph-based analysis
- Automated job feed curation
- REST API for external access

