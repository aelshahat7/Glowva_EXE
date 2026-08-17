"""
Glowva ERP - Products View
"""

import customtkinter as ctk
import database as db
from views.product_edit_dialog import ProductEditDialog


class ProductsView(ctk.CTkFrame):

    PAGE_SIZE = 50

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.page = 0
        self.products = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_search()
        self._build_list_area()
        self._build_pagination()

        self._refresh_list()

    # ==========================================================
    # Header
    # ==========================================================

    def _build_header(self):

        header = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        header.grid(
            row=0,
            column=0,
            padx=30,
            pady=(25, 10),
            sticky="ew"
        )

        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="الأصناف",
            font=ctk.CTkFont(
                size=24,
                weight="bold"
            )
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ctk.CTkButton(
            header,
            text="➕ صنف جديد",
            fg_color="#27AE60",
            hover_color="#1E8449",
            command=self._add_new
        ).grid(
            row=0,
            column=1,
            sticky="e"
        )

    # ==========================================================
    # Search
    # ==========================================================

    def _build_search(self):

        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text="دوّري باسم الصنف أو الفئة...",
            font=ctk.CTkFont(size=14)
        )

        self.search_entry.grid(
            row=1,
            column=0,
            padx=30,
            pady=(0, 15),
            sticky="ew"
        )

        self.search_entry.bind(
            "<KeyRelease>",
            self._on_search
        )

    def _on_search(self, event=None):

        self.page = 0
        self._refresh_list()

    # ==========================================================
    # List
    # ==========================================================

    def _build_list_area(self):

        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )

        self.list_frame.grid(
            row=2,
            column=0,
            padx=30,
            pady=(0, 10),
            sticky="nsew"
        )

        self.list_frame.grid_columnconfigure(
            0,
            weight=1
        )

    # ==========================================================
    # Pagination
    # ==========================================================

    def _build_pagination(self):

        self.pagination_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.pagination_frame.grid(
            row=3,
            column=0,
            padx=30,
            pady=(0, 15),
            sticky="ew"
        )

        self.pagination_frame.grid_columnconfigure(
            1,
            weight=1
        )

        self.prev_button = ctk.CTkButton(
            self.pagination_frame,
            text="→ السابق",
            width=100,
            command=self._previous_page
        )

        self.prev_button.grid(
            row=0,
            column=0,
            padx=5
        )

        self.page_label = ctk.CTkLabel(
            self.pagination_frame,
            text="صفحة 1"
        )

        self.page_label.grid(
            row=0,
            column=1
        )

        self.next_button = ctk.CTkButton(
            self.pagination_frame,
            text="التالي ←",
            width=100,
            command=self._next_page
        )

        self.next_button.grid(
            row=0,
            column=2,
            padx=5
        )

    def _previous_page(self):

        if self.page > 0:

            self.page -= 1

            self._render_page()

    def _next_page(self):

        max_page = max(
            0,
            (len(self.products) - 1) // self.PAGE_SIZE
        )

        if self.page < max_page:

            self.page += 1

            self._render_page()

    # ==========================================================
    # Refresh
    # ==========================================================

    def _refresh_list(self):

        query = (
            self.search_entry
            .get()
            .strip()
            .lower()
        )

        # نقرأ البيانات من SQLite
        products = db.list_products()

        # Search
        if query:

            products = [
                p
                for p in products
                if query in p["name"].lower()
                or query in (p["category"] or "").lower()
            ]

        self.products = products

        # لو الصفحة الحالية خرجت عن العدد
        max_page = max(
            0,
            (len(self.products) - 1) // self.PAGE_SIZE
        )

        if self.page > max_page:
            self.page = max_page

        self._render_page()

    # ==========================================================
    # Render Current Page
    # ==========================================================

    def _render_page(self):

        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.products:

            ctk.CTkLabel(
                self.list_frame,
                text="مفيش أصناف تطابق البحث",
                text_color="gray50"
            ).pack(
                pady=30
            )

            self._update_pagination()

            return

        start = self.page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        page_products = self.products[start:end]

        # نحصل فقط على بيانات المخزون المطلوبة
        stock_rows = db.get_inventory()

        stock_by_id = {
            r["product_id"]: r
            for r in stock_rows
        }

        for product in page_products:

            self._render_row(
                product,
                stock_by_id.get(product["id"])
            )

        self._update_pagination()

    # ==========================================================
    # Pagination State
    # ==========================================================

    def _update_pagination(self):

        total = len(self.products)

        if total == 0:

            total_pages = 1
            current_page = 1

        else:

            total_pages = (
                (total - 1) // self.PAGE_SIZE
            ) + 1

            current_page = self.page + 1

        self.page_label.configure(
            text=f"صفحة {current_page} من {total_pages}   |   {total} صنف"
        )

        self.prev_button.configure(
            state="normal"
            if self.page > 0
            else "disabled"
        )

        self.next_button.configure(
            state="normal"
            if self.page < total_pages - 1
            else "disabled"
        )

    # ==========================================================
    # Add / Edit
    # ==========================================================

    def _add_new(self):

        ProductEditDialog(
            self.winfo_toplevel(),
            None,
            self._refresh_list
        )

    def _edit(self, product):

        ProductEditDialog(
            self.winfo_toplevel(),
            product,
            self._refresh_list
        )

    # ==========================================================
    # Product Row
    # ==========================================================

    def _render_row(
        self,
        product,
        stock_info
    ):

        buy_price = float(
            product["buy_price"] or 0
        )

        sell_price = float(
            product["sell_price"] or 0
        )

        margin = 0

        if sell_price > 0:

            margin = (
                (sell_price - buy_price)
                / sell_price
            ) * 100

        current_stock = (
            stock_info["current_stock"]
            if stock_info
            else 0
        )

        threshold = float(
            product["low_stock_threshold"] or 0
        )

        is_low = current_stock <= threshold

        row = ctk.CTkFrame(
            self.list_frame,
            fg_color=("gray92", "gray20"),
            corner_radius=8
        )

        row.pack(
            fill="x",
            pady=4
        )

        row.grid_columnconfigure(
            0,
            weight=1
        )

        top = ctk.CTkFrame(
            row,
            fg_color="transparent"
        )

        top.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=12,
            pady=(10, 2)
        )

        top.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            top,
            text=product["name"],
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            ),
            anchor="e"
        ).grid(
            row=0,
            column=1,
            sticky="e"
        )

        if product["category"]:

            ctk.CTkLabel(
                top,
                text=product["category"],
                text_color="gray50",
                font=ctk.CTkFont(size=12)
            ).grid(
                row=1,
                column=1,
                sticky="e"
            )

        ctk.CTkButton(
            top,
            text="✏️ تعديل",
            width=80,
            height=28,
            command=lambda p=product: self._edit(p)
        ).grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="w"
        )

        stats = ctk.CTkFrame(
            row,
            fg_color="transparent"
        )

        stats.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=12,
            pady=(2, 10)
        )

        def stat(
            label,
            value,
            color=None
        ):

            box = ctk.CTkFrame(
                stats,
                fg_color="transparent"
            )

            box.pack(
                side="right",
                padx=(14, 0)
            )

            ctk.CTkLabel(
                box,
                text=label,
                text_color="gray50",
                font=ctk.CTkFont(size=11)
            ).pack(
                anchor="e"
            )

            ctk.CTkLabel(
                box,
                text=value,
                font=ctk.CTkFont(
                    size=13,
                    weight="bold"
                ),
                text_color=color or ("gray10", "gray90")
            ).pack(
                anchor="e"
            )

        stat(
            "سعر البيع",
            f"{sell_price:,.2f}"
        )

        stat(
            "سعر الشراء",
            f"{buy_price:,.2f}"
        )

        stat(
            "هامش الربح",
            f"{margin:.0f}%"
        )

        stat(
            "المخزون",
            f"{current_stock:,.0f}",
            color="#C0392B"
            if is_low
            else "#27AE60"
        )