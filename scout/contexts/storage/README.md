# Storage Context

The storage context provides database abstraction and persistence functionality for SCOUT. It implements a clean separation between generic database operations and backend-specific implementations.

## Architecture

The storage context follows a layered architecture with a factory pattern:

```
┌─────────────────────────────────────────┐
│  Factory Layer (getter.py)              │
│  - get_database_wrapper()               │
│  - backend_class_map                    │
│  - ALLOWED_BACKENDS                     │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Generic Layer (database.py)            │
│  - DatabaseConfig (configuration)       │
│  - DatabaseWrapper (abstract base)      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Backend Layer (e.g. postgres.py)       │
│  - PostgreSQLWrapper                    │
│  - PostgreSQLSchemaInspector            │
│  - postgres_connect                     │
└─────────────────────────────────────────┘
```

## Core Components

### `get_database_wrapper()` ([getter.py](getter.py))

**Responsibility:** Factory function that creates appropriate database wrapper based on `DATABASE_BACKEND` environment variable.

**What it does:**
- Reads `DATABASE_BACKEND` from environment
- Maps backend name to implementation class via `backend_class_map`
- Returns appropriate `DatabaseWrapper` implementation
- Optionally ensures database exists via `ensure_exists` parameter

**What it doesn't do:**
- Does not expose backend implementation details

**Usage:**
```python
# Primary interface for getting database wrappers
config = DatabaseConfig.from_env(name="my_database")
db = get_database_wrapper(config, ensure_exists=True)

# Now you can use the database wrapper
conn = db.connect()
df = db.export_df("SELECT * FROM users")
```

**Adding new backends:**
To support a new database backend (e.g., MySQL), update `getter.py`:
```python
backend_class_map = {
    "postgres": PostgreSQLWrapper,
    "mysql": MySQLWrapper,  # Add your implementation
}
```

---

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
config = DatabaseConfig.from_env(name="my_database", table="my_table")

# Manual construction
config = DatabaseConfig(
    host="localhost",
    port=5432,
    user="postgres",
    password="secret",
    name="my_database",
    table="my_table"
)

# Access connection string
engine = create_engine(config.connection_string)
```

---

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
        # Implementation specific to your database
        pass

    def get_column_values(self, table_name: str, column_name: str) -> list:
        # Implementation specific to your database
        pass

    # ... implement other abstract methods
```

---

### `SchemaInspector` ([schema.py](schema.py))

**Responsibility:** Abstract base class for database schema introspection.

**What it does:**
- Defines interface for schema inspection:
  - `list_tables()` - List all tables in database
  - `list_columns(table)` - List columns in a table
  - `tree(draw=True)` - Generate schema tree visualization
- Provides database-agnostic tree generation logic

**What it doesn't do:**
- Does not modify schema (read-only)
- Does not validate schema structure
- Does not manage migrations

---

## Utility Functions

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
    ├── users
    │   ├── id
    │   └── name
    └── posts
        ├── id
        └── user_id
```

---

## Design Principles

### Bounded Context

The storage context is a **bounded context** in Domain-Driven Design terms:
- It owns database connection and persistence logic
- Other contexts depend on storage, but storage is independent
- **Implementation details are hidden** - Other contexts only see the factory and abstract interfaces

### Factory Pattern

The storage context uses a factory pattern to decouple clients from specific implementations:
- Call `get_database_wrapper(config)` instead of directly instantiating a specific wrapper
- The `DATABASE_BACKEND` environment variable determines which implementation is returned
- Implementation classes (`PostgreSQLWrapper`, `PostgreSQLSchemaInspector`) are not exported
- This allows adding new database backends without changing code outside of the storage context

### Separation of Concerns

1. **Factory** (`get_database_wrapper`) - Gets implementation based on configuration
2. **Abstract interfaces** (`DatabaseWrapper`, `SchemaInspector`) - Define classes
3. **Backend implementations** - Implement classes
4. **Configuration** (`DatabaseConfig`) - Separate from connection management

---