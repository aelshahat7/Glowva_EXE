"""
Glowva ERP - Inventory View
عرض المخزون الفعلي فقط مع Pagination
"""

import customtkinter as ctk
import database as db
from rtl import rtl


FILTERS = [
    ("available", "المتوفر"),
    ("low", "قرّب يخلص"),
    ("out", "خلص خالص"),
]


class InventoryView(ctk.CTkFrame):

    PAGE_SIZE = 50

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.current_filter = "available"
        self.all_items = []
        self.filtered_items = []
        self.page = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_summary()
        self._build_filters()
        self._build_list_area()
        self._build_pagination()
        self._refresh()

    def _build_header(self):
        ctk.CTkLabel(
            self, text=rtl("المخزون"), font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=30, pady=(25, 10), sticky="e")

    def _build_summary(self):
        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, padx=30, pady=(0, 10), sticky="ew")
        for i in range(3):
            self.summary_frame.grid_columnconfigure(i, weight=1)

    def _render_summary(self):
        for widget in self.summary_frame.winfo_children():
            widget.destroy()

        available = len([item for item in self.all_items if item["current_stock"] > 0])
        low = len([item for item in self.all_items if 0 < item["current_stock"] <= item["low_stock_threshold"]])
        out = len([item for item in self.all_items if item["current_stock"] <= 0])

        cards = [
            ("الأصناف المتوفرة", available, "#27AE60"),
            ("قرّب يخلص", low, "#E67E22"),
            ("خلص خالص", out, "#C0392B"),
        ]

        for i, (label, value, color) in enumerate(cards):
            card = ctk.CTkFrame(self.summary_frame, corner_radius=10)
            card.grid(row=0, column=2 - i, padx=6, sticky="nsew")
            ctk.CTkLabel(card, text=rtl(label), font=ctk.CTkFont(size=13), text_color="gray50", anchor="e").pack(padx=15, pady=(15, 2), anchor="e")
            ctk.CTkLabel(card, text=str(value), font=ctk.CTkFont(size=22, weight="bold"), text_color=color).pack(padx=15, pady=(0, 15), anchor="e")

    def _build_filters(self):
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=2, column=0, padx=30, pady=(5, 10), sticky="e")
        self.filter_buttons = {}
        for key, label in FILTERS:
            btn = ctk.CTkButton(filter_frame, text=rtl(label), width=110, command=lambda k=key: self._set_filter(k))
            btn.pack(side="right", padx=4)
            self.filter_buttons[key] = btn
        self._update_filter_styles()

    def _set_filter(self, key):
        self.current_filter = key
        self.page = 0
        self._update_filter_styles()
        self._apply_filter()

    def _update_filter_styles(self):
        for key, btn in self.filter_buttons.items():
            btn.configure(fg_color="#1f6aa5" if key == self.current_filter else "gray50")

    def _build_list_area(self):
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.grid(row=3, column=0, padx=30, pady=(0, 10), sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _build_pagination(self):
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.grid(row=4, column=0, padx=30, pady=(0, 15), sticky="ew")
        self.pagination_frame.grid_columnconfigure(1, weight=1)

        self.prev_button = ctk.CTkButton(self.pagination_frame, text=rtl("السابق →"), width=100, command=self._previous_page)
        self.prev_button.grid(row=0, column=2, padx=5)

        self.page_label = ctk.CTkLabel(self.pagination_frame, text=rtl("صفحة 1"))
        self.page_label.grid(row=0, column=1)

        self.next_button = ctk.CTkButton(self.pagination_frame, text=rtl("التالي ←"), width=100, command=self._next_page)
        self.next_button.grid(row=0, column=0, padx=5)

    def _previous_page(self):
        if self.page > 0:
            self.page -= 1
            self._render_page()

    def _next_page(self):
        max_page = max(0, (len(self.filtered_items) - 1) // self.PAGE_SIZE)
        if self.page < max_page:
            self.page += 1
            self._render_page()

    def _update_pagination(self):
        total = len(self.filtered_items)
        total_pages = 1 if total == 0 else ((total - 1) // self.PAGE_SIZE) + 1
        current_page = 1 if total == 0 else self.page + 1
        self.page_label.configure(text=rtl(f"صفحة {current_page} من {total_pages} | {total} صنف"))
        self.prev_button.configure(state="normal" if self.page > 0 else "disabled")
        self.next_button.configure(state="normal" if self.page < total_pages - 1 else "disabled")

    def _refresh(self):
        self.all_items = db.get_inventory()
        self._render_summary()
        self._apply_filter()

    def _apply_filter(self):
        if self.current_filter == "available":
            self.filtered_items = [item for item in self.all_items if item["current_stock"] > 0]
        elif self.current_filter == "low":
            self.filtered_items = [item for item in self.all_items if 0 < item["current_stock"] <= item["low_stock_threshold"]]
        elif self.current_filter == "out":
            self.filtered_items = [item for item in self.all_items if item["current_stock"] <= 0]
        else:
            self.filtered_items = []

        self.filtered_items.sort(key=lambda item: item["current_stock"])

        max_page = max(0, (len(self.filtered_items) - 1) // self.PAGE_SIZE)
        if self.page > max_page:
            self.page = max_page
        self._render_page()

    def _render_page(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.filtered_items:
            if self.current_filter == "available":
                msg = rtl("مفيش أصناف عليها مخزون حاليًا")
            elif self.current_filter == "low":
                msg = rtl("مفيش أصناف قرّبت تخلص 👍")
            else:
                msg = rtl("مفيش أصناف خلصت")
            ctk.CTkLabel(self.list_frame, text=msg, text_color="gray50").pack(pady=30)
            self._update_pagination()
            return

        start = self.page * self.PAGE_SIZE
        for item in self.filtered_items[start:start + self.PAGE_SIZE]:
            self._render_row(item)
        self._update_pagination()

    def _render_row(self, item):
        stock = float(item["current_stock"] or 0)
        threshold = float(item["low_stock_threshold"] or 0)
        is_out = stock <= 0
        is_low = stock > 0 and stock <= threshold
        color = "#C0392B" if is_out else ("#E67E22" if is_low else "#27AE60")

        row = ctk.CTkFrame(self.list_frame, fg_color=("gray92", "gray20"), corner_radius=8)
        row.pack(fill="x", pady=4)
        row.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text=rtl(item["product_name"]), font=ctk.CTkFont(size=14, weight="bold"), anchor="e").grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(top, text=f"{stock:,.0f}", font=ctk.CTkFont(size=18, weight="bold"), text_color=color, anchor="e").grid(row=0, column=0, sticky="e")

        detail = (
            f"افتتاحي {item['opening_stock']:,.0f}"
            f"   +   اتوردت {item['total_purchased']:,.0f}"
            f"   -   اتباعت {item['total_sold']:,.0f}"
            f"   |   حد التنبيه {threshold:,.0f}"
        )
        ctk.CTkLabel(row, text=rtl(detail), text_color="gray50", font=ctk.CTkFont(size=11), anchor="e").grid(row=1, column=0, sticky="e", padx=12, pady=(0, 10))
