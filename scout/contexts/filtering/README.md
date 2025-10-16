# Filtering Context

The filtering context provides declarative job filtering through YAML configuration files. It implements the **producer side** of the event-driven architecture, logging status changes without directly modifying the database.

## Responsibilities

**What filtering context owns:**
- Job filtering logic and criteria
- Event production (logs status changes)
- Config-driven filter orchestration

**What it does NOT do:**
- Database updates (storage context does this via events)
- Data collection (scraping context)

---

## FilterPipeline: Config-Driven Filtering

The main entry point for filtering is `FilterPipeline`, which reads configuration from YAML and applies filters sequentially.

### Basic Usage

**1. Configure filters** (`config/filters.yaml`):
```yaml
sql_filters:
  min_salary: 0 # Minimum max_salary (0 means do not perform salary filtering)
  max_age_days: 7 # Maximum days since posting  (0 means do not perform age filtering)
  onsite_locations: # Locations to include
    - "MD"
  hybrid_locations: # Locations to include for hybrid jobs
    - "DC"
  remote: true # Include remote positions

keyword_filters: # exclude if NONE of these keywords found in corresponding column
  required_keywords:
    - "machine learning"
  description_column: "Description"

red_flags: # exclude if ANY of these keywords found in corresponding column
  - 1: 
    column: "Description"
    bool_out_column: "No_Corporate_Buzzwords"
    flags:
      - "synergy"
  - 2:
    column: "Job Title"
    bool_out_column: "Not_a_Manager"
    flags:
      - "Manager"

active_check:
  enabled: false # Slow, disable by default
```

**2. Apply filters**:
```python
from scout.contexts.filtering import FilterPipeline

pipeline = FilterPipeline("config/filters.yaml")

# SQL filtering (fast, database-side)
query = pipeline.build_sql_query()
df = scraper.import_db_as_df(query=query)

# Pandas filtering (flexible, memory-side)
df_filtered = pipeline.apply_filters(df, verbose=True)
```

**Output:**
```
Starting with 160 jobs
After keyword filtering: 50 jobs
After 'Description' red flag filtering: 30 jobs
After 'Job Title' red flag filtering: 25 jobs

Filtered out 150 jobs (83.3%)
```


## Event Production

Filtering context **logs events** when detecting status changes, allowing storage context to process them later (respects bounded contexts).

### `check_active()` Function

Checks if URLs are still valid and logs status changes to event log.

```python
from scout.contexts.filtering import check_active

df_with_status = check_active(df, database_name="ACME_Corp_job_listings")
# Returns dataframe with added "Inactive" column
# Logs events to outs/logs/listing_status_changed.txt

```

**Event log format** (JSON Lines - one JSON per line):
```json
{"timestamp": "2024-10-14T10:30:00", "database": "ACME_Corp_job_listings", "url": "https://...", "old_status": "active", "new_status": "inactive"}
{"timestamp": "2024-10-14T10:31:00", "database": "ACME_Corp_job_listings", "url": "https://...", "old_status": "unknown", "new_status": "inactive"}
```

**Why JSON Lines?**
- Append-friendly: new events added without rewriting entire file
- Can process line-by-line without loading everything into memory
- Crash-resistant: partial writes don't corrupt previous events

---

## Configuration Reference

### SQL Filters

Fast, runs on database before loading data into memory.

**Location Logic:**
- `onsite_locations`: Jobs in these locations (any remote status)
- `hybrid_locations`: Jobs in these locations AND remote = 'Hybrid'
- `remote: true`: Fully remote jobs (any location)
- Combined with OR logic

#### Keyword Filters in Pandas

Must contain at least one `required_keyword`

### Red Flag Filters

Exclude if column contains any flag

**How it works:**
- Each entry checks ONE column for multiple flags
- Creates boolean column: `{column}_OK` (or custom name)
- Filters out rows where any flag found
- Fully generic - works on any column

### Active URL Check

Validates URLs via HTTP requests (slow to respect servers)

**When enabled:**
- Makes HTTP request for each URL
- Logs events if status changed (active → inactive)
- Use sparingly (network overhead)



## Design Philosophy

### Configuration Instead of Hard-Coding

**❌ Hardcoded values**
```python
df = df[df["max_salary"] >= 999999999] # 💲💲💲
df = df[df["Description"].str.contains(" AI | ML")]
```

**✅ Declarative config**
```yaml
sql_filters:
  min_salary: 999999999
keyword_filters:
  required_keywords:
    - " AI "
    - "ML"
```

### Read-Only Filtering

Filtering context **never writes to database**:

```python
# ✅ Correct: logs events
df = check_active(df, database_name="my_db")  # Writes to outs/logs/listing_status_changed.txt

# Later, storage context updates database
process_status_events("my_db")
```

This respects bounded context principles and enables async/scheduled processing.
