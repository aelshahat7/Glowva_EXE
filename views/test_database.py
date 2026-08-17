"""
Test suite for database.py - run BEFORE building any GUI on top of this,
since bugs here would be much harder to spot once hidden behind a UI.
"""
import os
import sys
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import database as db

passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"PASS: {label}")
    else:
        failed += 1
        print(f"FAIL: {label}")


# Use a temp file DB for testing, never touch the real one
test_db = tempfile.mktemp(suffix=".db")

# --- Test 1: schema creation ---
db.init_db(test_db)
with db.get_connection(test_db) as conn:
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
check("all 8 tables created", all(t in tables for t in
      ["products", "customers", "suppliers", "orders", "order_items", "purchases", "purchase_items", "profit_payouts"]))

with db.get_connection(test_db) as conn:
    views = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'"
    ).fetchall()]
check("inventory view created", "inventory" in views)

# --- Test 2: init_db is safe to call twice (idempotent, no data loss) ---
pid = db.add_product("Test Product Idempotency", sell_price=100, buy_price=60, db_path=test_db)
db.init_db(test_db)  # call again
with db.get_connection(test_db) as conn:
    row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
check("re-running init_db does not wipe existing data", row is not None and row["sell_price"] == 100)

# --- Test 3: get_or_create_product avoids duplicates ---
id1 = db.get_or_create_product("Cream A", buy_price=50, db_path=test_db)
id2 = db.get_or_create_product("Cream A", buy_price=999, db_path=test_db)  # same name again
check("get_or_create_product returns same id for same name", id1 == id2)
with db.get_connection(test_db) as conn:
    row = conn.execute("SELECT buy_price FROM products WHERE id = ?", (id1,)).fetchone()
check("get_or_create_product does NOT overwrite existing buy_price on repeat call", row["buy_price"] == 50)

# --- Test 4: realistic order with multiple line items (mirrors the screenshot scenario:
#     one order split across products, auto-creating customer + products) ---
order_items = [
    {"product_name": "Moisturizer X", "quantity": 3, "unit_price": 150},
    {"product_name": "Perfume Y", "quantity": 1, "unit_price": 450},
]
order_id = db.create_order("2026-08-11", "Sara Ahmed", order_items,
                            customer_phone="0100000000", db_path=test_db)
total = db.get_order_total(order_id, db_path=test_db)
check("order total = 3*150 + 1*450 = 900", total == 900)

with db.get_connection(test_db) as conn:
    cust = conn.execute("SELECT * FROM customers WHERE name = ?", ("Sara Ahmed",)).fetchone()
check("customer auto-created from order", cust is not None and cust["phone"] == "0100000000")

    # calling create_order again for the SAME customer must NOT create a duplicate
order_id2 = db.create_order("2026-08-12", "Sara Ahmed", [
    {"product_name": "Moisturizer X", "quantity": 1, "unit_price": 150}
], db_path=test_db)
with db.get_connection(test_db) as conn:
    count = conn.execute("SELECT COUNT(*) AS c FROM customers WHERE name = ?", ("Sara Ahmed",)).fetchone()["c"]
check("second order for same customer does not duplicate the customer row", count == 1)

# --- Test 5: purchase + inventory calculation, the most important piece ---
db.add_product("Widget Z", sell_price=200, buy_price=100, opening_stock=10,
                low_stock_threshold=5, db_path=test_db)

db.create_purchase("2026-08-01", "Supplier One", [
    {"product_name": "Widget Z", "quantity": 20, "unit_price": 100}
], db_path=test_db)

db.create_order("2026-08-05", "Buyer One", [
    {"product_name": "Widget Z", "quantity": 3, "unit_price": 200}
], db_path=test_db)

inv = db.get_inventory(test_db)
widget = next(r for r in inv if r["product_name"] == "Widget Z")
check("Widget Z current_stock = opening(10) + purchased(20) - sold(3) = 27",
      widget["current_stock"] == 27)
check("Widget Z not flagged low stock (27 > 5)", widget["current_stock"] > widget["low_stock_threshold"])

# --- Test 6: low stock detection ---
db.add_product("Almost Gone", sell_price=50, buy_price=20, opening_stock=2,
                low_stock_threshold=5, db_path=test_db)
low = db.get_low_stock(test_db)
check("low-stock product correctly flagged", any(r["product_name"] == "Almost Gone" for r in low))
check("healthy-stock product NOT in low-stock list", not any(r["product_name"] == "Widget Z" for r in low))

# --- Test 7: cascade delete - deleting an order removes its line items ---
items_before = None
with db.get_connection(test_db) as conn:
    items_before = conn.execute(
        "SELECT COUNT(*) AS c FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchone()["c"]
check("order has line items before delete", items_before == 2)

with db.get_connection(test_db) as conn:
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))

with db.get_connection(test_db) as conn:
    items_after = conn.execute(
        "SELECT COUNT(*) AS c FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchone()["c"]
check("cascade delete removed the order's line items automatically", items_after == 0)

# --- Test 8: foreign key enforcement actually works (not silently ignored) ---
fk_blocked = False
try:
    with db.get_connection(test_db) as conn:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
            "VALUES (99999, 99999, 1, 1)"
        )
except sqlite3.IntegrityError:
    fk_blocked = True
check("foreign key constraint blocks orphaned order_items", fk_blocked)

# --- Test 9: dashboard summary math ---
summary = db.get_dashboard_summary(test_db)
check("dashboard summary returns a dict with expected keys",
      all(k in summary for k in ["total_sales", "total_purchases", "profit", "margin", "low_stock_count"]))

# --- Test 10: zero-sales month doesn't crash margin calculation (division guard) ---
empty_db = tempfile.mktemp(suffix=".db")
db.init_db(empty_db)
empty_summary = db.get_dashboard_summary(empty_db)
check("empty database: margin=0 with no crash (division guard)", empty_summary["margin"] == 0)
check("empty database: total_sales=0", empty_summary["total_sales"] == 0)
os.remove(empty_db)

# --- Test 11: discount is actually subtracted from order total (the bug just fixed) ---
disc_order_id = db.create_order("2026-08-11", "Discount Tester", [
    {"product_name": "Widget Z", "quantity": 2, "unit_price": 100},
], discount=30, db_path=test_db)
disc_total = db.get_order_total(disc_order_id, db_path=test_db)
check("order total subtracts discount: 2*100 - 30 = 170", disc_total == 170)

# --- Test 12: list_recent_orders returns correct discounted totals, newest first ---
recent = db.list_recent_orders(limit=5, db_path=test_db)
check("list_recent_orders returns results", len(recent) > 0)
check("list_recent_orders newest order first", recent[0]["id"] == disc_order_id)
matching = next((o for o in recent if o["id"] == disc_order_id), None)
check("list_recent_orders total matches get_order_total (discount applied)",
      matching is not None and matching["total"] == 170)

# --- Test 13: list_customers ---
customers = db.list_customers(test_db)
check("list_customers returns a non-empty list after orders were created",
      len(customers) > 0 and any(c["name"] == "Sara Ahmed" for c in customers))

# --- Test 14: dashboard total_sales also reflects discounts now ---
summary_after_discount = db.get_dashboard_summary(test_db)
# recompute expected: sum of all order_items minus sum of all order discounts across the whole test db
with db.get_connection(test_db) as conn:
    expected_subtotal = conn.execute(
        "SELECT COALESCE(SUM(quantity*unit_price),0) AS t FROM order_items"
    ).fetchone()["t"]
    expected_discount = conn.execute(
        "SELECT COALESCE(SUM(discount),0) AS t FROM orders"
    ).fetchone()["t"]
check("dashboard total_sales = subtotal - total discounts",
      summary_after_discount["total_sales"] == expected_subtotal - expected_discount)

# --- Test 15: profit payouts basic CRUD ---
payout_id = db.add_profit_payout("2026-08-13", 500, reason="مصاريف شخصية", db_path=test_db)
check("add_profit_payout returns an id", payout_id is not None)

payouts = db.list_profit_payouts(db_path=test_db)
check("list_profit_payouts returns the new payout", len(payouts) == 1 and payouts[0]["amount"] == 500)
check("payout reason stored correctly", payouts[0]["reason"] == "مصاريف شخصية")

db.add_profit_payout("2026-08-14", 200, db_path=test_db)
payouts2 = db.list_profit_payouts(db_path=test_db)
check("second payout, newest first", len(payouts2) == 2 and payouts2[0]["amount"] == 200)

db.delete_profit_payout(payout_id, db_path=test_db)
payouts3 = db.list_profit_payouts(db_path=test_db)
check("delete_profit_payout removes exactly the right one", len(payouts3) == 1 and payouts3[0]["amount"] == 200)

# --- Test 16: dashboard available_balance correctly subtracts payouts from profit ---
db.add_product("Payout Test Product", sell_price=100, buy_price=40, opening_stock=50, db_path=test_db)
db.create_order("2026-08-13", "Payout Buyer", [
    {"product_name": "Payout Test Product", "quantity": 10, "unit_price": 100}
], db_path=test_db)
# sales=1000, purchases=0 so far in THIS product's chain -> profit contribution +1000
# plus whatever earlier tests already put in this same test_db... so compute expected fresh:
summary = db.get_dashboard_summary(test_db)
expected_available = summary["profit"] - summary["total_payouts"]
check("available_balance = profit - total_payouts (formula matches)",
      summary["available_balance"] == expected_available)
check("total_payouts reflects remaining payout (200) after the delete above",
      summary["total_payouts"] == 200)

os.remove(test_db)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
