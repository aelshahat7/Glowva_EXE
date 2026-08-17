"""
Glowva ERP Desktop - Database Layer
====================================
SQLite database: schema creation, connection management, and CRUD helpers.
This is the foundation the GUI will sit on top of. Designed to mirror the
Google Sheets structure we already built (Products, Orders, Purchases,
Customers, Suppliers, Inventory, Drawings) but as a proper relational
schema now that we're not limited by spreadsheet constraints.
"""

import sqlite3
import os
from datetime import date, datetime
from contextlib import contextmanager

DB_FILENAME = "glowva_erp.db"


def get_db_path():
    """Database lives next to the app, in a user-writable location."""
    app_dir = os.path.join(os.path.expanduser("~"), "GlowvaERP")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, DB_FILENAME)


@contextmanager
def get_connection(db_path=None):
    """Context manager: opens a connection with foreign keys enforced,
    commits on success, rolls back on error, always closes."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT,
    sell_price REAL NOT NULL DEFAULT 0,
    buy_price REAL NOT NULL DEFAULT 0,
    opening_stock REAL NOT NULL DEFAULT 0,
    low_stock_threshold REAL NOT NULL DEFAULT 5,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    phone2 TEXT,
    address TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact_info TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_date TEXT NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    payment_status TEXT NOT NULL DEFAULT 'مدفوع',
    order_status TEXT NOT NULL DEFAULT 'قيد التنفيذ',
    discount REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_date TEXT NOT NULL,
    supplier_id INTEGER REFERENCES suppliers(id),
    invoice_number TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS purchase_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS profit_payouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payout_date TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIEW IF NOT EXISTS inventory AS
SELECT
    p.id AS product_id,
    p.name AS product_name,
    p.opening_stock,
    COALESCE(purch.total_purchased, 0) AS total_purchased,
    COALESCE(sold.total_sold, 0) AS total_sold,
    p.opening_stock + COALESCE(purch.total_purchased, 0) - COALESCE(sold.total_sold, 0) AS current_stock,
    p.low_stock_threshold
FROM products p
LEFT JOIN (
    SELECT product_id, SUM(quantity) AS total_purchased
    FROM purchase_items GROUP BY product_id
) purch ON purch.product_id = p.id
LEFT JOIN (
    SELECT product_id, SUM(quantity) AS total_sold
    FROM order_items GROUP BY product_id
) sold ON sold.product_id = p.id;
"""


def init_db(db_path=None):
    """Creates all tables/views if they don't already exist. Safe to call
    every time the app starts - never drops or overwrites existing data."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        # cleanup: "drawings" was renamed to "profit_payouts" before any
        # real data existed under it - drop the stale empty table if
        # present from earlier testing. No-op after the first run.
        conn.execute("DROP TABLE IF EXISTS drawings")


# ---------------------------------------------------------------
# Products
# ---------------------------------------------------------------

def add_product(name, category="", sell_price=0, buy_price=0,
                 opening_stock=0, low_stock_threshold=5, db_path=None):
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO products (name, category, sell_price, buy_price, "
            "opening_stock, low_stock_threshold) VALUES (?, ?, ?, ?, ?, ?)",
            (name, category, sell_price, buy_price, opening_stock, low_stock_threshold)
        )
        return cur.lastrowid


def get_or_create_product(name, buy_price=None, db_path=None):
    """Mirrors ensureProductExists() from the Apps Script version -
    used when a new product name appears in a purchase for the first time."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT id FROM products WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO products (name, buy_price) VALUES (?, ?)",
            (name, buy_price or 0)
        )
        return cur.lastrowid


def list_products(db_path=None):
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM products ORDER BY name").fetchall()]


def update_product(product_id, name, category, sell_price, buy_price,
                    opening_stock, low_stock_threshold, db_path=None):
    """Raises sqlite3.IntegrityError if renaming to a name that already
    belongs to a different product - the caller should catch this and
    show a friendly message rather than letting it crash."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE products SET name=?, category=?, sell_price=?, buy_price=?, "
            "opening_stock=?, low_stock_threshold=? WHERE id=?",
            (name, category, sell_price, buy_price, opening_stock, low_stock_threshold, product_id)
        )


# ---------------------------------------------------------------
# Customers / Suppliers
# ---------------------------------------------------------------

def get_or_create_customer(name, phone="", db_path=None):
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT id FROM customers WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO customers (name, phone) VALUES (?, ?)", (name, phone)
        )
        return cur.lastrowid


def get_or_create_supplier(name, db_path=None):
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT id FROM suppliers WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute("INSERT INTO suppliers (name) VALUES (?)", (name,))
        return cur.lastrowid


# ---------------------------------------------------------------
# Orders (header + line items together, like a real invoice)
# ---------------------------------------------------------------

def create_order(order_date, customer_name, items, customer_phone="",
                  payment_status="مدفوع", order_status="قيد التنفيذ",
                  discount=0, db_path=None):
    """items: list of dicts {product_name, quantity, unit_price}
    Returns the new order_id. Whole order is one transaction - either
    all lines are saved or none are (no half-written orders)."""
    with get_connection(db_path) as conn:
        customer_row = conn.execute(
            "SELECT id FROM customers WHERE name = ?", (customer_name,)
        ).fetchone()
        if customer_row:
            customer_id = customer_row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO customers (name, phone) VALUES (?, ?)",
                (customer_name, customer_phone)
            )
            customer_id = cur.lastrowid

        cur = conn.execute(
            "INSERT INTO orders (order_date, customer_id, payment_status, "
            "order_status, discount) VALUES (?, ?, ?, ?, ?)",
            (order_date, customer_id, payment_status, order_status, discount)
        )
        order_id = cur.lastrowid

        for item in items:
            prod_row = conn.execute(
                "SELECT id FROM products WHERE name = ?", (item["product_name"],)
            ).fetchone()
            if prod_row:
                product_id = prod_row["id"]
            else:
                pcur = conn.execute(
                    "INSERT INTO products (name, sell_price) VALUES (?, ?)",
                    (item["product_name"], item["unit_price"])
                )
                product_id = pcur.lastrowid

            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                "VALUES (?, ?, ?, ?)",
                (order_id, product_id, item["quantity"], item["unit_price"])
            )

        return order_id


def get_order_total(order_id, db_path=None):
    """Line items subtotal minus the order-level discount."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS subtotal, "
            "o.discount AS discount FROM orders o "
            "LEFT JOIN order_items oi ON oi.order_id = o.id "
            "WHERE o.id = ? GROUP BY o.id",
            (order_id,)
        ).fetchone()
        if not row:
            return 0
        return row["subtotal"] - row["discount"]


def list_customers(db_path=None):
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM customers ORDER BY name").fetchall()]


def list_customers_with_stats(db_path=None):
    """Total spend per customer. Computed via a subquery that resolves
    each order's total FIRST (line items sum minus that order's discount),
    then aggregates by customer - joining orders straight to order_items
    and summing o.discount directly would count the discount once per
    line item instead of once per order, silently inflating totals for
    any multi-item order."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT c.*, "
            "COUNT(o.id) AS order_count, "
            "COALESCE(SUM(o.order_total), 0) AS total_spend "
            "FROM customers c "
            "LEFT JOIN ("
            "  SELECT o.id, o.customer_id, "
            "  COALESCE(SUM(oi.quantity * oi.unit_price), 0) - o.discount AS order_total "
            "  FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.id "
            "  GROUP BY o.id"
            ") o ON o.customer_id = c.id "
            "GROUP BY c.id ORDER BY c.name"
        ).fetchall()
        return [dict(r) for r in rows]


def get_customer_orders(customer_id, limit=50, db_path=None):
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT o.id, o.order_date, o.payment_status, o.order_status, "
            "COALESCE(SUM(oi.quantity * oi.unit_price), 0) - o.discount AS total "
            "FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.id "
            "WHERE o.customer_id = ? GROUP BY o.id ORDER BY o.id DESC LIMIT ?",
            (customer_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def list_suppliers(db_path=None):
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()]


def list_suppliers_with_stats(db_path=None):
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT s.*, "
            "COUNT(DISTINCT p.id) AS purchase_count, "
            "COALESCE(SUM(pi.quantity * pi.unit_price), 0) AS total_purchased "
            "FROM suppliers s "
            "LEFT JOIN purchases p ON p.supplier_id = s.id "
            "LEFT JOIN purchase_items pi ON pi.purchase_id = p.id "
            "GROUP BY s.id ORDER BY s.name"
        ).fetchall()
        return [dict(r) for r in rows]


def get_supplier_purchases(supplier_id, limit=50, db_path=None):
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT p.id, p.purchase_date, p.invoice_number, "
            "COALESCE(SUM(pi.quantity * pi.unit_price), 0) AS total "
            "FROM purchases p LEFT JOIN purchase_items pi ON pi.purchase_id = p.id "
            "WHERE p.supplier_id = ? GROUP BY p.id ORDER BY p.id DESC LIMIT ?",
            (supplier_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def list_recent_orders(limit=15, db_path=None):
    """Order list with computed totals (subtotal - discount), newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT o.id, o.order_date, o.payment_status, o.order_status, o.discount, "
            "COALESCE(c.name, '') AS customer_name, "
            "COALESCE(SUM(oi.quantity * oi.unit_price), 0) - o.discount AS total "
            "FROM orders o "
            "LEFT JOIN customers c ON c.id = o.customer_id "
            "LEFT JOIN order_items oi ON oi.order_id = o.id "
            "GROUP BY o.id ORDER BY o.id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_recent_purchases(limit=15, db_path=None):
    """Purchase list with computed totals, newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT p.id, p.purchase_date, p.invoice_number, "
            "COALESCE(s.name, '') AS supplier_name, "
            "COALESCE(SUM(pi.quantity * pi.unit_price), 0) AS total "
            "FROM purchases p "
            "LEFT JOIN suppliers s ON s.id = p.supplier_id "
            "LEFT JOIN purchase_items pi ON pi.purchase_id = p.id "
            "GROUP BY p.id ORDER BY p.id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_last_purchase_price(product_name, db_path=None):
    """Most recent price actually paid for this product, falling back to the
    product's stored buy_price if it has never been purchased yet."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT pi.unit_price FROM purchase_items pi "
            "JOIN products p ON p.id = pi.product_id "
            "JOIN purchases pu ON pu.id = pi.purchase_id "
            "WHERE p.name = ? "
            "ORDER BY pu.id DESC, pi.id DESC LIMIT 1",
            (product_name,)
        ).fetchone()
        if row:
            return row["unit_price"]

        prow = conn.execute(
            "SELECT buy_price FROM products WHERE name = ?", (product_name,)
        ).fetchone()
        return prow["buy_price"] if prow else 0


# ---------------------------------------------------------------
# Purchases (header + line items)
# ---------------------------------------------------------------

def create_purchase(purchase_date, supplier_name, items, invoice_number="", db_path=None):
    """items: list of dicts {product_name, quantity, unit_price}"""
    with get_connection(db_path) as conn:
        supp_row = conn.execute(
            "SELECT id FROM suppliers WHERE name = ?", (supplier_name,)
        ).fetchone()
        supplier_id = supp_row["id"] if supp_row else conn.execute(
            "INSERT INTO suppliers (name) VALUES (?)", (supplier_name,)
        ).lastrowid

        cur = conn.execute(
            "INSERT INTO purchases (purchase_date, supplier_id, invoice_number) "
            "VALUES (?, ?, ?)",
            (purchase_date, supplier_id, invoice_number)
        )
        purchase_id = cur.lastrowid

        for item in items:
            prod_row = conn.execute(
                "SELECT id FROM products WHERE name = ?", (item["product_name"],)
            ).fetchone()
            if prod_row:
                product_id = prod_row["id"]
            else:
                pcur = conn.execute(
                    "INSERT INTO products (name, buy_price) VALUES (?, ?)",
                    (item["product_name"], item["unit_price"])
                )
                product_id = pcur.lastrowid

            conn.execute(
                "INSERT INTO purchase_items (purchase_id, product_id, quantity, unit_price) "
                "VALUES (?, ?, ?, ?)",
                (purchase_id, product_id, item["quantity"], item["unit_price"])
            )

        return purchase_id


# ---------------------------------------------------------------
# Inventory / Dashboard queries
# ---------------------------------------------------------------

def get_inventory(db_path=None):
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM inventory ORDER BY product_name"
        ).fetchall()]


def get_low_stock(db_path=None):
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM inventory WHERE current_stock <= low_stock_threshold "
            "ORDER BY current_stock ASC"
        ).fetchall()]


# ---------------------------------------------------------------
# Profit payouts (money taken out of the business for personal use -
# does not reduce business profit, only the cash still available in it)
# ---------------------------------------------------------------

def add_profit_payout(payout_date, amount, reason="", db_path=None):
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO profit_payouts (payout_date, amount, reason) VALUES (?, ?, ?)",
            (payout_date, amount, reason)
        )
        return cur.lastrowid


def list_profit_payouts(limit=50, db_path=None):
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM profit_payouts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def delete_profit_payout(payout_id, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM profit_payouts WHERE id = ?", (payout_id,))


def get_dashboard_summary(db_path=None):
    with get_connection(db_path) as conn:
        subtotal = conn.execute(
            "SELECT COALESCE(SUM(quantity * unit_price), 0) AS total FROM order_items"
        ).fetchone()["total"]
        total_discount = conn.execute(
            "SELECT COALESCE(SUM(discount), 0) AS total FROM orders"
        ).fetchone()["total"]
        sales = subtotal - total_discount

        purchases = conn.execute(
            "SELECT COALESCE(SUM(quantity * unit_price), 0) AS total FROM purchase_items"
        ).fetchone()["total"]

        total_payouts = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM profit_payouts"
        ).fetchone()["total"]

        low_stock_count = conn.execute(
            "SELECT COUNT(*) AS c FROM inventory WHERE current_stock <= low_stock_threshold"
        ).fetchone()["c"]

        order_count = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]

        profit = sales - purchases

        return {
            "total_sales": sales,
            "total_purchases": purchases,
            "profit": profit,
            "margin": (profit / sales) if sales > 0 else 0,
            "total_payouts": total_payouts,
            "available_balance": profit - total_payouts,
            "low_stock_count": low_stock_count,
            "order_count": order_count,
        }
