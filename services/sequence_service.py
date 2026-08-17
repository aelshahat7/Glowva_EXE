"""Sequential business codes for products, parties and documents."""

PREFIXES = {
    "product": "PRD",
    "customer": "CUS",
    "supplier": "SUP",
    "sale": "SAL",
    "purchase": "PUR",
}


def next_code(conn, sequence_key):
    """Atomically reserve and return the next human-facing code."""
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
