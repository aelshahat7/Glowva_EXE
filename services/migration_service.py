"""One-time/idempotent database migration for human-facing ERP codes."""

from services.sequence_service import PREFIXES, sync_sequence_to_existing_data


def _add_column_if_missing(conn, table, column, definition):
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def _populate_codes(conn):
    mappings = [
        ("product", "products", "PRD"),
        ("customer", "customers", "CUS"),
        ("supplier", "suppliers", "SUP"),
    ]

    for sequence_key, table, prefix in mappings:
        rows = conn.execute(
            f"SELECT id FROM {table} WHERE code IS NULL OR TRIM(code) = '' ORDER BY id"
        ).fetchall()

        for row in rows:
            # Existing database IDs are already stable and monotonic.
            code = f"{prefix}-{int(row['id']):06d}"
            conn.execute(
                f"UPDATE {table} SET code = ? WHERE id = ?",
                (code, row["id"]),
            )

    for table, code_column, prefix in (
        ("orders", "document_no", "SAL"),
        ("purchases", "document_no", "PUR"),
    ):
        rows = conn.execute(
            f"SELECT id FROM {table} WHERE {code_column} IS NULL OR TRIM({code_column}) = '' ORDER BY id"
        ).fetchall()

        for row in rows:
            code = f"{prefix}-{int(row['id']):06d}"
            conn.execute(
                f"UPDATE {table} SET {code_column} = ? WHERE id = ?",
                (code, row["id"]),
            )


def run(conn):
    """Apply the identifier foundation without deleting or rewriting data."""
    # Human-facing code columns.
    _add_column_if_missing(conn, "products", "code", "TEXT")
    _add_column_if_missing(conn, "customers", "code", "TEXT")
    _add_column_if_missing(conn, "suppliers", "code", "TEXT")
    _add_column_if_missing(conn, "orders", "document_no", "TEXT")
    _add_column_if_missing(conn, "purchases", "document_no", "TEXT")

    # Persistent sequence cursors.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sequences (
            sequence_key TEXT PRIMARY KEY,
            next_value INTEGER NOT NULL
        )
        """
    )

    _populate_codes(conn)

    # Unique codes prevent accidental duplication.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_products_code ON products(code)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_code ON customers(code)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_suppliers_code ON suppliers(code)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_document_no ON orders(document_no)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_document_no ON purchases(document_no)"
    )

    # Start each sequence after the highest code already present.
    sync_sequence_to_existing_data(conn, "product", "products")
    sync_sequence_to_existing_data(conn, "customer", "customers")
    sync_sequence_to_existing_data(conn, "supplier", "suppliers")
    sync_sequence_to_existing_data(conn, "sale", "orders", "document_no")
    sync_sequence_to_existing_data(conn, "purchase", "purchases", "document_no")


def run_database_migration(db_path=None):
    import sqlite3

    from database import get_db_path

    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        run(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
