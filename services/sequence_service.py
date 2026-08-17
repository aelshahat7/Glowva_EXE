"""Sequential business codes for products, parties and documents."""

PREFIXES = {
    "product": "PRD",
    "customer": "CUS",
    "supplier": "SUP",
    "sale": "SAL",
    "purchase": "PUR",
}


def next_code(conn, sequence_key):
    """Reserve and return the next human-facing code inside the caller's transaction."""
    prefix = PREFIXES[sequence_key]
    row = conn.execute(
        "SELECT next_value FROM sequences WHERE sequence_key = ?",
        (sequence_key,),
    ).fetchone()

    if row is None:
        value = 1
        conn.execute(
            "INSERT INTO sequences (sequence_key, next_value) VALUES (?, ?)",
            (sequence_key, 2),
        )
    else:
        value = int(row["next_value"])
        conn.execute(
            "UPDATE sequences SET next_value = ? WHERE sequence_key = ?",
            (value + 1, sequence_key),
        )

    return f"{prefix}-{value:06d}"


def sync_sequence_to_existing_data(conn, sequence_key, table, code_column="code"):
    """Move a sequence cursor past the largest existing numeric code."""
    prefix = PREFIXES[sequence_key]

    row = conn.execute(
        f"""
        SELECT MAX(CAST(SUBSTR({code_column}, ?) AS INTEGER)) AS max_value
        FROM {table}
        WHERE {code_column} LIKE ?
        """,
        (len(prefix) + 2, f"{prefix}-%"),
    ).fetchone()

    max_value = int(row["max_value"] or 0)
    next_value = max_value + 1

    conn.execute(
        """
        INSERT INTO sequences (sequence_key, next_value)
        VALUES (?, ?)
        ON CONFLICT(sequence_key)
        DO UPDATE SET next_value = MAX(sequences.next_value, excluded.next_value)
        """,
        (sequence_key, next_value),
    )
