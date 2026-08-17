"""
Glowva ERP - Data Importer
===========================
Imports the existing Glowva Excel workbook into the desktop SQLite database.

Usage:
    python import_data.py
    python import_data.py "Glowva_ERP.xlsx"

The importer:
- backs up the existing database before replacing it
- rebuilds the database from the Excel source
- imports Products, Customers, Suppliers, Orders, Purchases, Drawings
- derives inventory from opening stock + purchases - sales
- does NOT import Dashboard/Monthly because those are derived reports
- prints a verification summary and inventory mismatches
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_XLSX = BASE_DIR / "Glowva_ERP.xlsx"
APP_DB_DIR = Path.home() / "GlowvaERP"
DB_PATH = APP_DB_DIR / "glowva_erp.db"


NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def number(value, default=0.0):
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return default


def excel_date(value):
    """Convert an Excel serial date or common date string to YYYY-MM-DD."""
    if value in (None, ""):
        return ""

    if isinstance(value, (int, float)):
        try:
            base = datetime(1899, 12, 30)
            return (base + timedelta(days=float(value))).date().isoformat()
        except Exception:
            return ""

    text = str(value).strip()
    if not text:
        return ""

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass

    return text


def read_xlsx(path: Path):
    """Read worksheet values using only the Python standard library."""
    with zipfile.ZipFile(path, "r") as z:
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", NS):
                shared_strings.append(
                    "".join(t.text or "" for t in si.iter("{%s}t" % NS["a"]))
                )

        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}

        result = {}

        for sheet in workbook.find("a:sheets", NS):
            name = sheet.attrib["name"]
            rid = sheet.attrib["{%s}id" % NS["r"]]
            target = relmap[rid]
            if not target.startswith("xl/"):
                target = "xl/" + target

            root = ET.fromstring(z.read(target))
            rows = []

            for row in root.findall(".//a:sheetData/a:row", NS):
                cells = {}
                for cell in row.findall("a:c", NS):
                    ref = cell.attrib.get("r", "")
                    value_node = cell.find("a:v", NS)

                    if value_node is None:
                        value = ""
                    else:
                        value = value_node.text or ""

                    if cell.attrib.get("t") == "s" and value != "":
                        value = shared_strings[int(value)]

                    cells[ref] = value

                if cells:
                    rows.append(cells)

            result[name] = rows

    return result


def col_letter(ref):
    letters = "".join(ch for ch in ref if ch.isalpha())
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch.upper()) - 64
    return n


def row_values(row):
    if not row:
        return []

    max_col = max(col_letter(ref) for ref in row)
    values = [""] * max_col

    for ref, value in row.items():
        values[col_letter(ref) - 1] = value

    return values


def get_rows(sheets, name):
    raw = sheets.get(name, [])
    return [row_values(r) for r in raw]


def nonblank_rows(rows):
    return [r for r in rows if any(clean(v) for v in r)]


def backup_existing_db():
    APP_DB_DIR.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = APP_DB_DIR / f"glowva_erp_before_import_{stamp}.db"
    shutil.copy2(DB_PATH, backup)
    return backup


def reset_database():
    """Rebuild the database using the application's existing schema."""
    import database as db

    if DB_PATH.exists():
        DB_PATH.unlink()

    db.init_db(str(DB_PATH))


def ensure_product(conn, name, product_info, opening_info):
    name = clean(name)
    if not name:
        return None

    cur = conn.execute("SELECT id FROM products WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]

    info = product_info.get(name, {})
    inv = opening_info.get(name, {})

    conn.execute(
        """
        INSERT INTO products
            (name, category, sell_price, buy_price, opening_stock, low_stock_threshold)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            info.get("category", ""),
            info.get("sell_price", 0),
            info.get("buy_price", 0),
            inv.get("opening", 0),
            inv.get("threshold", 5),
        ),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def import_all(xlsx_path: Path):
    import database as db

    if not xlsx_path.exists():
        raise FileNotFoundError(f"الملف غير موجود: {xlsx_path}")

    sheets = read_xlsx(xlsx_path)

    required = ["Products", "Inventory", "Customers", "Suppliers", "Orders", "Purchases"]
    missing = [name for name in required if name not in sheets]
    if missing:
        raise ValueError("ملفات/شيتات ناقصة: " + ", ".join(missing))

    backup = backup_existing_db()
    reset_database()

    product_rows = nonblank_rows(get_rows(sheets, "Products")[1:])
    inventory_rows = nonblank_rows(get_rows(sheets, "Inventory")[1:])
    customer_rows = nonblank_rows(get_rows(sheets, "Customers")[1:])
    supplier_rows = nonblank_rows(get_rows(sheets, "Suppliers")[1:])
    order_rows = nonblank_rows(get_rows(sheets, "Orders")[1:])
    purchase_rows = nonblank_rows(get_rows(sheets, "Purchases")[1:])
    drawing_rows = nonblank_rows(get_rows(sheets, "Drawings")[1:])

    product_info = {}
    for r in product_rows:
        name = clean(r[0] if len(r) > 0 else "")
        if not name:
            continue
        product_info[name] = {
            "category": clean(r[1] if len(r) > 1 else ""),
            "sell_price": number(r[2] if len(r) > 2 else 0),
            "buy_price": number(r[3] if len(r) > 3 else 0),
        }

    opening_info = {}
    for r in inventory_rows:
        name = clean(r[0] if len(r) > 0 else "")
        if not name:
            continue
        opening_info[name] = {
            "opening": number(r[1] if len(r) > 1 else 0),
            "threshold": number(r[5] if len(r) > 5 else 5, 5),
        }

    # Include any inventory/purchase/order-only products.
    all_product_names = set(product_info) | set(opening_info)
    for r in purchase_rows:
        if len(r) > 2 and clean(r[2]):
            all_product_names.add(clean(r[2]))
    for r in order_rows:
        if len(r) > 4 and clean(r[4]):
            all_product_names.add(clean(r[4]))

    customer_map = {}
    supplier_map = {}
    product_map = {}

    with db.get_connection(str(DB_PATH)) as conn:
        # Products
        for name in sorted(all_product_names):
            product_map[name] = ensure_product(
                conn, name, product_info, opening_info
            )

        # Customers
        for r in customer_rows:
            name = clean(r[0] if len(r) > 0 else "")
            if not name:
                continue

            phone = clean(r[1] if len(r) > 1 else "")
            phone2 = clean(r[2] if len(r) > 2 else "")
            address = clean(r[3] if len(r) > 3 else "")
            notes = clean(r[4] if len(r) > 4 else "")

            conn.execute(
                """
                INSERT INTO customers (name, phone, phone2, address, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, phone, phone2, address, notes),
            )
            customer_map[name] = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

        # Supplier
        for r in supplier_rows:
            name = clean(r[0] if len(r) > 0 else "")
            if not name:
                continue

            contact = clean(r[1] if len(r) > 1 else "")
            conn.execute(
                "INSERT INTO suppliers (name, contact_info) VALUES (?, ?)",
                (name, contact),
            )
            supplier_map[name] = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

        # Fallback cash customer.
        cash_customer = "عميل نقدي"
        cur = conn.execute("SELECT id FROM customers WHERE name = ?", (cash_customer,))
        row = cur.fetchone()
        if row:
            cash_customer_id = row[0]
        else:
            conn.execute("INSERT INTO customers (name) VALUES (?)", (cash_customer,))
            cash_customer_id = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

        # Orders grouped by original order ID.
        orders_grouped = defaultdict(list)
        for r in order_rows:
            original_id = clean(r[0] if len(r) > 0 else "")
            key = original_id or f"ROW-{len(orders_grouped) + 1}"
            orders_grouped[key].append(r)

        imported_orders = 0
        imported_order_items = 0

        for original_id, rows in orders_grouped.items():
            first = rows[0]

            order_date = excel_date(first[1] if len(first) > 1 else "")
            customer_name = clean(first[2] if len(first) > 2 else "") or cash_customer
            phone = clean(first[3] if len(first) > 3 else "")
            payment_status = clean(first[9] if len(first) > 9 else "") or "مدفوع"
            order_status = clean(first[10] if len(first) > 10 else "") or "قيد التنفيذ"

            customer_id = customer_map.get(customer_name, cash_customer_id)
            if customer_name != cash_customer and customer_name not in customer_map:
                conn.execute(
                    "INSERT INTO customers (name, phone) VALUES (?, ?)",
                    (customer_name, phone),
                )
                customer_id = conn.execute(
                    "SELECT last_insert_rowid()"
                ).fetchone()[0]
                customer_map[customer_name] = customer_id

            subtotal = sum(number(r[7] if len(r) > 7 else 0) for r in rows)
            invoice_total = number(first[11] if len(first) > 11 else 0)

            if invoice_total > 0:
                discount = max(0, subtotal - invoice_total)
            else:
                # Fallback: use the first explicit discount, rather than summing
                # a possibly repeated invoice-level value across every line.
                discount = next(
                    (number(r[8]) for r in rows[0:1] if len(r) > 8),
                    0,
                )

            cur = conn.execute(
                """
                INSERT INTO orders
                    (order_date, customer_id, payment_status, order_status, discount)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_date or datetime.now().date().isoformat(),
                    customer_id,
                    payment_status,
                    order_status,
                    discount,
                ),
            )
            order_id = cur.lastrowid
            imported_orders += 1

            for r in rows:
                product_name = clean(r[4] if len(r) > 4 else "")
                qty = number(r[5] if len(r) > 5 else 0)
                unit_price = number(r[6] if len(r) > 6 else 0)

                if not product_name or qty == 0:
                    continue

                product_id = product_map.get(product_name)
                if product_id is None:
                    product_id = ensure_product(
                        conn, product_name, product_info, opening_info
                    )
                    product_map[product_name] = product_id

                conn.execute(
                    """
                    INSERT INTO order_items
                        (order_id, product_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (order_id, product_id, qty, unit_price),
                )
                imported_order_items += 1

        # Purchases grouped by date + supplier + invoice.
        # If invoice number is blank, each source row becomes its own purchase,
        # because there is no safe key to merge unrelated lines.
        purchase_groups = []
        grouped = defaultdict(list)

        for idx, r in enumerate(purchase_rows, start=2):
            purchase_date = excel_date(r[0] if len(r) > 0 else "")
            supplier_name = clean(r[1] if len(r) > 1 else "") or "مورد غير محدد"
            invoice = clean(r[6] if len(r) > 6 else "")

            if invoice:
                key = (purchase_date, supplier_name, invoice)
                grouped[key].append(r)
            else:
                purchase_groups.append((idx, [r]))

        for key, rows in grouped.items():
            purchase_groups.append((key, rows))

        imported_purchases = 0
        imported_purchase_items = 0

        for key, rows in purchase_groups:
            first = rows[0]
            purchase_date = excel_date(first[0] if len(first) > 0 else "")
            supplier_name = clean(first[1] if len(first) > 1 else "") or "مورد غير محدد"
            invoice = clean(first[6] if len(first) > 6 else "")

            supplier_id = supplier_map.get(supplier_name)
            if supplier_id is None:
                conn.execute(
                    "INSERT INTO suppliers (name) VALUES (?)",
                    (supplier_name,),
                )
                supplier_id = conn.execute(
                    "SELECT last_insert_rowid()"
                ).fetchone()[0]
                supplier_map[supplier_name] = supplier_id

            cur = conn.execute(
                """
                INSERT INTO purchases
                    (purchase_date, supplier_id, invoice_number)
                VALUES (?, ?, ?)
                """,
                (
                    purchase_date or datetime.now().date().isoformat(),
                    supplier_id,
                    invoice,
                ),
            )
            purchase_id = cur.lastrowid
            imported_purchases += 1

            for r in rows:
                product_name = clean(r[2] if len(r) > 2 else "")
                qty = number(r[3] if len(r) > 3 else 0)
                unit_price = number(r[4] if len(r) > 4 else 0)

                if not product_name or qty == 0:
                    continue

                product_id = product_map.get(product_name)
                if product_id is None:
                    product_id = ensure_product(
                        conn, product_name, product_info, opening_info
                    )
                    product_map[product_name] = product_id

                conn.execute(
                    """
                    INSERT INTO purchase_items
                        (purchase_id, product_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (purchase_id, product_id, qty, unit_price),
                )
                imported_purchase_items += 1

        # Drawings -> profit payouts.
        imported_payouts = 0
        for r in drawing_rows:
            payout_date = excel_date(r[0] if len(r) > 0 else "")
            amount = number(r[1] if len(r) > 1 else 0)
            reason = clean(r[2] if len(r) > 2 else "")

            if not amount:
                continue

            conn.execute(
                """
                INSERT INTO profit_payouts (payout_date, amount, reason)
                VALUES (?, ?, ?)
                """,
                (
                    payout_date or datetime.now().date().isoformat(),
                    amount,
                    reason,
                ),
            )
            imported_payouts += 1

        # Verification queries.
        counts = {
            "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "customers": conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "suppliers": conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0],
            "orders": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            "order_items": conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0],
            "purchases": conn.execute("SELECT COUNT(*) FROM purchases").fetchone()[0],
            "purchase_items": conn.execute("SELECT COUNT(*) FROM purchase_items").fetchone()[0],
            "profit_payouts": conn.execute("SELECT COUNT(*) FROM profit_payouts").fetchone()[0],
        }

        # Compare imported inventory against source Inventory sheet.
        mismatches = []
        for name, source in opening_info.items():
            row = conn.execute(
                """
                SELECT current_stock, low_stock_threshold
                FROM inventory
                WHERE product_name = ?
                """,
                (name,),
            ).fetchone()

            if not row:
                mismatches.append((name, "غير موجود في قاعدة البيانات", None, source["opening"]))
                continue

            current = float(row[0] or 0)
            threshold = float(row[1] or 0)

            # Current source inventory is not copied directly. It is recomputed
            # from opening + purchases - sales, which is the intended DB design.
            expected_current = source["opening"]
            purchased = conn.execute(
                """
                SELECT COALESCE(SUM(pi.quantity), 0)
                FROM purchase_items pi
                JOIN products p ON p.id = pi.product_id
                WHERE p.name = ?
                """,
                (name,),
            ).fetchone()[0]
            sold = conn.execute(
                """
                SELECT COALESCE(SUM(oi.quantity), 0)
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE p.name = ?
                """,
                (name,),
            ).fetchone()[0]
            expected_current += float(purchased or 0) - float(sold or 0)

            if abs(current - expected_current) > 1e-9:
                mismatches.append(
                    (name, "فرق في الرصيد", current, expected_current)
                )

        report = {
            "source": str(xlsx_path),
            "backup": str(backup) if backup else None,
            "counts": counts,
            "source_rows": {
                "products": len(product_rows),
                "customers": len(customer_rows),
                "suppliers": len(supplier_rows),
                "orders_lines": len(order_rows),
                "purchase_lines": len(purchase_rows),
                "drawings": len(drawing_rows),
            },
            "inventory_mismatches": mismatches[:50],
            "inventory_mismatch_count": len(mismatches),
        }

    return report


def main():
    xlsx_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_XLSX

    print("=" * 60)
    print("Glowva ERP - استيراد البيانات")
    print("=" * 60)
    print(f"المصدر: {xlsx_path}")
    print(f"قاعدة البيانات: {DB_PATH}")
    print()

    report = import_all(xlsx_path)

    print("تم الاستيراد بنجاح ✅")
    print()
    print("البيانات داخل قاعدة البيانات:")
    for key, value in report["counts"].items():
        print(f"  {key:20s}: {value}")

    print()
    print(f"نسخة احتياطية قديمة: {report['backup'] or 'لم تكن هناك قاعدة بيانات سابقة'}")
    print(f"فروقات المخزون: {report['inventory_mismatch_count']}")

    if report["inventory_mismatch_count"]:
        print()
        print("أول فروقات:")
        for item in report["inventory_mismatches"][:20]:
            print(" ", item)

    print()
    print("مهم: Dashboard و Monthly لم يتم استيرادهما، لأن التطبيق يحسبهما من قاعدة البيانات.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print("❌ فشل الاستيراد")
        print(type(exc).__name__ + ":", exc)
        raise
