# Storage Context

The storage context provides database abstraction and persistence for SCOUT. It implements clean separation between generic database operations and backend-specific implementations, following **bounded context** principles from Domain-Driven Design.

## Responsibilities

**What storage context owns:**
- Database connections and schema management
- Event consumption (maintenance workers)
- Archive management for processed events

**What it does NOT do:**
- Scraping or filtering logic (other contexts)
- Direct modification by external contexts (uses events)


### **Example Workflow:**
```python
# Primary interface for getting database wrappers
from scout.contexts.storage import get_database_wrapper, DatabaseConfig

config = DatabaseConfig.from_env(name="my_database")
db = get_database_wrapper(config, ensure_exists=True)

# Now use the database
df = db.export_df("SELECT * FROM listings WHERE status = 'active'")
```


## Core Components

### `DatabaseConfig` ([database.py](database.py))

**Responsibility:** Configuration dataclass for database connections.

**What it does:**
- Stores connection parameters (host, port, user, password, database name, table)
- Provides `from_env()` class method to load credentials from environment variables
- Generates PostgreSQL connection strings via `connection_string` property

**What it doesn't do:**
- Does not manage connections
- Does not validate database existence
- Does not perform any I/O operations

**Usage:**
```python
# From environment variables
config = DatabaseConfig.from_env(name="my_database", table="listings")

# Manual construction
config = DatabaseConfig(
    host="localhost",
    port=5432,
    user="postgres",
    password="secret",
    name="my_database",
    table="listings"
)
```

### `DatabaseWrapper` ([database.py](database.py))

**Responsibility:** Abstract base class defining the interface for database operations.

**What it does:**
- Defines abstract methods that all database backends must implement:
  - `connect()` - Create database connection
  - `get_column_values()` - Query column values
  - `export_df()` - Export query results as DataFrame
  - `_db_exists()` - Check database existence (static)
  - `_create_db()` - Create database (static)
- Provides `from_config()` class method for instantiation with optional database creation

**What it doesn't do:**
- Does not implement any backend-specific logic
- Does not manage connection pools
- Does not handle transactions

**Implementation pattern:**
```python
class MyDatabaseWrapper(DatabaseWrapper):
    def connect(self):
        # Your implementation
        pass

    def export_df(self, query: str) -> pd.DataFrame:
        # Your implementation
        pass

    # ... implement other abstract methods
```


## Architecture

### Factory Pattern

```
┌─────────────────────────────────┐
│  Factory Layer (getter.py)      │
│  get_database_wrapper()         │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Generic Layer (database.py)    │
│  DatabaseConfig, DatabaseWrapper│
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Backend Layer (postgres.py)    │
│  PostgreSQLWrapper              │
└─────────────────────────────────┘
```


### Event-Driven Communication

Storage context implements the **consumer side** of the broadcast-subscribe pattern. Other contexts (like filtering) produce events; storage consumes and processes them.

#### Event Flow

```
Filtering Context                  Storage Context
  (producer)                         (consumer)
      │                                  │
      │  check_active()                  │
      │  detects inactive URL            │
      │                                  │
      ├──> Event Log ────────────────>   │
      │    listing_status_changed.txt    │
      │    (JSON Lines format)           │
      │                                  │
      │                                  ▼
      │                        process_status_events()
      │                        reads log, updates DB
      │                                  │
      │                                  ▼
      │                        Archive processed events
      │                        to *_processed.txt
```

#### [maintenance.py](maintenance.py)

**`process_status_events(database_names=None)`**

Orchestrator function that processes status change events for one or more databases.
- Decouples event logging from processing (enabling async/scheduled processing)
- Respects bounded contexts (storage owns database, filtering doesn't)
- Can discover and process all databases automatically

```python
from scout.contexts.storage import process_status_events

# Process specified databases
results = process_status_events(["ACME_Corp_job_listings", "MomCorp_job_listings"])

# Process all databases found in events
results = process_status_events()
print(f"Processed: {results}")  # {'ACME_Corp_job_listings': 5, ...}
```

**`process_status_events_for_database(db_wrapper)`**

Lower-level function for processing events for a specific database.

```python
from scout.contexts.storage import get_database_wrapper, DatabaseConfig
from scout.contexts.storage import process_status_events_for_database

config = DatabaseConfig.from_env('my_database')
db = get_database_wrapper(config)

events_processed = process_status_events_for_database(db)
print(f"Updated {events_processed} listings")
```


## Design Principles

### Bounded Context

Storage context is isolated:
- Other contexts depend on storage, storage is independent
- External contexts communicate via events, not direct DB writes
- Implementation details (PostgreSQL specifics) hidden behind abstractions

### Event-Driven Updates

**Old approach (violates bounded contexts):**
```python
# Filtering context directly updates database
df = check_active(df, database_name="my_db")
db.execute("UPDATE listings SET status = 'inactive' WHERE ...")
```

**New approach (respects bounded contexts):**
```python
# Filtering logs events
df = check_active(df, database_name="my_db")  # Logs to outs/logs/listing_status_changed.txt

# Storage processes events (later, asynchronously)
process_status_events("my_db")  # Reads log, updates database
```

### Separation of Concerns

1. **Factory** - Selects implementation based on configuration
2. **Abstract interfaces** - Define database-agnostic operations
3. **Backend implementations** - PostgreSQL, MySQL, etc.
4. **Configuration** - Separate from connection management
5. **Event consumers** - Process cross-context events



## Utility Functions


### `get_database_wrapper()` (Factory)

Primary interface - automatically selects backend based on `DATABASE_BACKEND` env var:

```python
# Returns PostgreSQLWrapper if DATABASE_BACKEND=postgres
db = get_database_wrapper(config, ensure_exists=True)
```

---


### `draw_db_tree()` ([schema.py](schema.py))

**Responsibility:** Visualize database schema as a tree structure.

**What it does:**
- Takes numpy array of `[table, column]` pairs
- Prints hierarchical tree visualization to console

**What it doesn't do:**
- Does not query the database (expects pre-processed data)
- Does not return the visualization as string (prints directly)

**Usage:**
```python
from scout.contexts.storage.schema import draw_db_tree
import numpy as np

tree_data = np.array([
    ["users", "id"],
    ["users", "name"],
    ["posts", "id"],
    ["posts", "user_id"],
])

draw_db_tree(tree_data, "my_database")
```

**Output:**
```
└── my_database
    ├── posts
    │   ├── id
    │   └── user_id
    └── users
        ├── id
        └── name
```