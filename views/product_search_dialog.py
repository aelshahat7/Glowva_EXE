"""
Product search popup - the pattern from the e-Stock Pharmacy reference
("بحث عن صنف"): a small window with a live search box and a real
multi-column results table (code / name / price / stock) instead of one
giant dropdown or a list of plain text buttons.
Built generic (takes any product list + a callback) so it can be reused
by Orders or Purchases with different secondary columns.
"""

import customtkinter as ctk
import database as db

COLUMN_WEIGHTS = (0, 1, 0, 0)  # كود ثابت / اسم يمدد / سعر ثابت / عمود رابع ثابت


class ProductSearchDialog(ctk.CTkToplevel):

    def __init__(self, parent, products, on_select, subtitle_key="buy_price", subtitle_label="آخر سعر"):
        """
        products: list of dicts, each must have 'id' and 'name' keys
        on_select: callback(product_dict) called when the user picks one
        subtitle_key / subtitle_label: which extra field to show as the
            4th column (e.g. buy_price for Purchases, current_stock for
            Orders)
        """
        super().__init__(parent)

        self.title("بحث عن صنف")
        self.geometry("640x520")
        self.transient(parent)
        self.grab_set()

        self.products = products
        self.on_select = on_select
        self.subtitle_key = subtitle_key
        self.subtitle_label = subtitle_label

        # current_stock lives in a separate inventory table, not on the
        # product dict itself, so pull it once here if it's the column
        # this dialog was asked to show (Orders uses this; Purchases
        # asks for buy_price instead, which IS already on the product).
        self.stock_by_id = {}
        if self.subtitle_key == "current_stock":
            self.stock_by_id = {
                row["product_id"]: row["current_stock"] for row in db.get_inventory()
            }

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.search_entry = ctk.CTkEntry(
            self, placeholder_text="اكتبي اسم الصنف أو الكود...", font=ctk.CTkFont(size=14)
        )
        self.search_entry.grid(row=0, column=0, padx=15, pady=(15, 8), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        self._build_table_header()

        self.results_frame = ctk.CTkScrollableFrame(self, fg_color=("gray95", "gray14"))
        self.results_frame.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="nsew")
        for col, weight in enumerate(COLUMN_WEIGHTS):
            self.results_frame.grid_columnconfigure(col, weight=weight)

        self._render_results(self.products)
        self.after(100, self.search_entry.focus)

    def _build_table_header(self):
        header = ctk.CTkFrame(self, fg_color=("gray85", "gray22"), corner_radius=6)
        header.grid(row=1, column=0, padx=15, sticky="ew")
        for col, weight in enumerate(COLUMN_WEIGHTS):
            header.grid_columnconfigure(col, weight=weight)

        if self.subtitle_key == "current_stock":
            # The subtitle column IS stock here, so there's no separate
            # 4th stock column to add.
            labels = ["كود", "اسم الصنف", self.subtitle_label, ""]
        else:
            labels = ["كود", "اسم الصنف", self.subtitle_label, "المخزون"]

        for col, text in enumerate(labels):
            ctk.CTkLabel(
                header, text=text, font=ctk.CTkFont(size=12, weight="bold"), anchor="e"
            ).grid(row=0, column=col, padx=10, pady=6, sticky="ew")

    def _on_search_change(self, event=None):
        query = self.search_entry.get().strip().lower()
        if not query:
            filtered = self.products
        else:
            filtered = [
                p for p in self.products
                if query in p["name"].lower() or query in str(p.get("id", "")).lower()
            ]
        self._render_results(filtered)

    def _render_results(self, products):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        if not products:
            ctk.CTkLabel(self.results_frame, text="مفيش نتائج", text_color="gray50").grid(
                row=0, column=0, columnspan=4, pady=30)
            return

        shown = products[:50]
        for row_index, p in enumerate(shown):
            self._render_row(row_index, p)

        if len(products) > 50:
            ctk.CTkLabel(
                self.results_frame, text=f"...وكمان {len(products)-50} نتيجة، دقّقي البحث أكتر",
                text_color="gray50", font=ctk.CTkFont(size=11)
            ).grid(row=len(shown), column=0, columnspan=4, pady=8)

    def _render_row(self, row_index, product):
        bg = ("gray95", "gray14") if row_index % 2 == 0 else ("gray90", "gray17")

        if self.subtitle_key == "current_stock":
            # current_stock isn't on the product dict (it's inventory-only,
            # joined via stock_by_id in __init__) - read it from there.
            subtitle_value = self.stock_by_id.get(product.get("id"), 0) or 0
            fourth_text = ""
        else:
            subtitle_value = product.get(self.subtitle_key, 0) or 0
            fourth_text = f"{self.stock_by_id.get(product.get('id'), 0):,.0f}"

        cells = [
            str(product.get("id", "")),
            product["name"],
            f"{subtitle_value:,.2f}",
            fourth_text,
        ]

        for col, text in enumerate(cells):
            cell = ctk.CTkLabel(
                self.results_frame, text=text, anchor="e", fg_color=bg,
                font=ctk.CTkFont(size=13), cursor="hand2"
            )
            cell.grid(row=row_index, column=col, padx=10, pady=6, sticky="ew")
            cell.bind("<Button-1>", lambda e, prod=product: self._select(prod))

    def _select(self, product):
        self.on_select(product)
        self.destroy()
