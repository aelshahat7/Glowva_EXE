"""Sales and purchase returns.

Returns are kept in dedicated tables for audit/history, while a negative
adjustment line is appended to the original invoice transaction so the
existing inventory, sales, purchases, profit, and available-balance queries
immediately reflect the return without changing the original invoice header.
"""

from __future__ import annotations

from datetime import date
import sqlite3
import database as db



def initialize_returns():
    """Create return tables and add return-adjustment flags to line items."""
    with db.get_connection() as conn:
        _ensure_column(conn, "order_items", "is_return_adjustment")
        _ensure_column(conn, "purchase_items", "is_return_adjustment")

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sales_returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                return_date TEXT NOT NULL,
                order_id INTEGER NOT NULL REFERENCES orders(id),
                customer_id INTEGER REFERENCES customers(id),
                total REAL NOT NULL DEFAULT 0,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sales_return_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sales_return_id INTEGER NOT NULL REFERENCES sales_returns(id) ON DELETE CASCADE,
                original_order_item_id INTEGER NOT NULL REFERENCES order_items(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                cost_price REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS purchase_returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                return_date TEXT NOT NULL,
                purchase_id INTEGER NOT NULL REFERENCES purchases(id),
                supplier_id INTEGER REFERENCES suppliers(id),
                total REAL NOT NULL DEFAULT 0,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS purchase_return_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_return_id INTEGER NOT NULL REFERENCES purchase_returns(id) ON DELETE CASCADE,
                original_purchase_item_id INTEGER NOT NULL REFERENCES purchase_items(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL
            );
            """
        )


def _ensure_column(conn, table, column):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0"
        )


def list_sales_invoices(limit=200):
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT o.id, o.order_date,
                   COALESCE(c.name, '') AS customer_name,
                   COALESCE(SUM(oi.quantity * oi.unit_price), 0) - o.discount AS total
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            LEFT JOIN order_items oi
              ON oi.order_id = o.id AND oi.is_return_adjustment = 0
            GROUP BY o.id
            HAVING COALESCE(SUM(oi.quantity * oi.unit_price), 0) > 0
            ORDER BY o.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_sales_return_lines(order_id):
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT oi.id AS order_item_id,
                   oi.product_id,
                   p.name AS product_name,
                   oi.quantity AS sold_quantity,
                   oi.unit_price,
                   p.buy_price AS cost_price,
                   COALESCE((
                       SELECT SUM(sri.quantity)
                       FROM sales_return_items sri
                       WHERE sri.original_order_item_id = oi.id
                   ), 0) AS already_returned
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = ?
              AND oi.is_return_adjustment = 0
              AND oi.quantity > 0
            ORDER BY oi.id
            """,
            (order_id,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["available_quantity"] = max(
                0.0, float(item["sold_quantity"]) - float(item["already_returned"])
            )
            result.append(item)
        return result


def create_sales_return(order_id, items, reason="", return_date=None):
    """items: [{order_item_id, quantity}]"""
    initialize_returns()
    return_date = return_date or date.today().isoformat()

    with db.get_connection() as conn:
        order = conn.execute(
            "SELECT id, customer_id FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if not order:
            raise ValueError("الفاتورة غير موجودة")

        clean_items = []
        total = 0.0
        for item in items:
            qty = float(item.get("quantity", 0) or 0)
            if qty <= 0:
                continue

            row = conn.execute(
                """
                SELECT oi.id, oi.product_id, oi.quantity, oi.unit_price,
                       p.buy_price AS cost_price,
                       COALESCE((
                           SELECT SUM(sri.quantity)
                           FROM sales_return_items sri
                           WHERE sri.original_order_item_id = oi.id
                       ), 0) AS already_returned
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.id = ? AND oi.order_id = ? AND oi.is_return_adjustment = 0
                """,
                (item["order_item_id"], order_id),
            ).fetchone()
            if not row:
                raise ValueError("أحد الأصناف غير موجود في الفاتورة")

            available = float(row["quantity"]) - float(row["already_returned"])
            if qty > available + 1e-9:
                raise ValueError("كمية المرتجع أكبر من الكمية المتاحة للمرتجع")

            total += qty * float(row["unit_price"])
            clean_items.append((row, qty))

        if not clean_items:
            raise ValueError("اختار كمية واحدة على الأقل للمرتجع")

        cur = conn.execute(
            """
            INSERT INTO sales_returns (return_date, order_id, customer_id, total, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (return_date, order_id, order["customer_id"], total, reason),
        )
        return_id = cur.lastrowid

        for row, qty in clean_items:
            conn.execute(
                """
                INSERT INTO sales_return_items
                    (sales_return_id, original_order_item_id, product_id, quantity, unit_price, cost_price)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (return_id, row["id"], row["product_id"], qty, row["unit_price"], row["cost_price"]),
            )

            # Negative line on the original invoice transaction. Existing
            # inventory/sales/profit calculations therefore include the return.
            conn.execute(
                """
                INSERT INTO order_items
                    (order_id, product_id, quantity, unit_price, is_return_adjustment)
                VALUES (?, ?, ?, ?, 1)
                """,
                (order_id, row["product_id"], -qty, row["unit_price"]),
            )

        return return_id


def list_purchase_invoices(limit=200):
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.purchase_date, p.invoice_number,
                   COALESCE(s.name, '') AS supplier_name,
                   COALESCE(SUM(pi.quantity * pi.unit_price), 0) AS total
            FROM purchases p
            LEFT JOIN suppliers s ON s.id = p.supplier_id
            LEFT JOIN purchase_items pi
              ON pi.purchase_id = p.id AND pi.is_return_adjustment = 0
            GROUP BY p.id
            HAVING COALESCE(SUM(pi.quantity * pi.unit_price), 0) > 0
            ORDER BY p.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_purchase_return_lines(purchase_id):
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT pi.id AS purchase_item_id,
                   pi.product_id,
                   p.name AS product_name,
                   pi.quantity AS purchased_quantity,
                   pi.unit_price,
                   COALESCE((
                       SELECT SUM(pri.quantity)
                       FROM purchase_return_items pri
                       WHERE pri.original_purchase_item_id = pi.id
                   ), 0) AS already_returned
            FROM purchase_items pi
            JOIN products p ON p.id = pi.product_id
            WHERE pi.purchase_id = ?
              AND pi.is_return_adjustment = 0
              AND pi.quantity > 0
            ORDER BY pi.id
            """,
            (purchase_id,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["available_quantity"] = max(
                0.0, float(item["purchased_quantity"]) - float(item["already_returned"])
            )
            result.append(item)
        return result


def create_purchase_return(purchase_id, items, reason="", return_date=None):
    """items: [{purchase_item_id, quantity}]"""
    initialize_returns()
    return_date = return_date or date.today().isoformat()

    with db.get_connection() as conn:
        purchase = conn.execute(
            "SELECT id, supplier_id FROM purchases WHERE id = ?", (purchase_id,)
        ).fetchone()
        if not purchase:
            raise ValueError("فاتورة التوريد غير موجودة")

        clean_items = []
        total = 0.0
        for item in items:
            qty = float(item.get("quantity", 0) or 0)
            if qty <= 0:
                continue

            row = conn.execute(
                """
                SELECT pi.id, pi.product_id, pi.quantity, pi.unit_price,
                       COALESCE((
                           SELECT SUM(pri.quantity)
                           FROM purchase_return_items pri
                           WHERE pri.original_purchase_item_id = pi.id
                       ), 0) AS already_returned
                FROM purchase_items pi
                WHERE pi.id = ? AND pi.purchase_id = ? AND pi.is_return_adjustment = 0
                """,
                (item["purchase_item_id"], purchase_id),
            ).fetchone()
            if not row:
                raise ValueError("أحد الأصناف غير موجود في فاتورة التوريد")

            available = float(row["quantity"]) - float(row["already_returned"])
            if qty > available + 1e-9:
                raise ValueError("كمية المرتجع أكبر من الكمية المتاحة للمرتجع")

            total += qty * float(row["unit_price"])
            clean_items.append((row, qty))

        if not clean_items:
            raise ValueError("اختار كمية واحدة على الأقل للمرتجع")

        cur = conn.execute(
            """
            INSERT INTO purchase_returns (return_date, purchase_id, supplier_id, total, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (return_date, purchase_id, purchase["supplier_id"], total, reason),
        )
        return_id = cur.lastrowid

        for row, qty in clean_items:
            conn.execute(
                """
                INSERT INTO purchase_return_items
                    (purchase_return_id, original_purchase_item_id, product_id, quantity, unit_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (return_id, row["id"], row["product_id"], qty, row["unit_price"]),
            )

            # Negative line on the original purchase transaction. Existing
            # inventory/purchases/profit/cash calculations therefore include it.
            conn.execute(
                """
                INSERT INTO purchase_items
                    (purchase_id, product_id, quantity, unit_price, is_return_adjustment)
                VALUES (?, ?, ?, ?, 1)
                """,
                (purchase_id, row["product_id"], -qty, row["unit_price"]),
            )

        return return_id


def get_sales_return_total():
    with db.get_connection() as conn:
        return conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS total FROM sales_returns"
        ).fetchone()["total"]


def get_purchase_return_total():
    with db.get_connection() as conn:
        return conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS total FROM purchase_returns"
        ).fetchone()["total"]
