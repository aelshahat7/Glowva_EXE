"""
Customers screen - who's buying, how much, and their full order history
on click (mirrors the "كشف حساب" pattern from the reference software).
"""

import customtkinter as ctk
import database as db
from rtl import rtl
from views.party_detail_dialog import PartyDetailDialog


class CustomersView(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_search()
        self._build_list_area()
        self._refresh_list()

    def _build_header(self):
        ctk.CTkLabel(
            self, text=rtl("العملاء"), font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=30, pady=(25, 10), sticky="e")

    def _build_search(self):
        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text=rtl("دوّري باسم العميل أو رقم الموبايل..."),
            font=ctk.CTkFont(size=14),
            justify="right",
        )
        self.search_entry.grid(row=1, column=0, padx=30, pady=(0, 15), sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_list())

    def _build_list_area(self):
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.grid(row=2, column=0, padx=30, pady=(0, 20), sticky="nsew")

    def _refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        customers = db.list_customers_with_stats()

        query = self.search_entry.get().strip().lower()
        if query:
            customers = [
                c for c in customers
                if query in c["name"].lower() or query in (c["phone"] or "").lower()
            ]

        if not customers:
            ctk.CTkLabel(
                self.list_frame,
                text=rtl("مفيش عملاء يطابقوا البحث"),
                text_color="gray50",
            ).pack(pady=30)
            return

        for customer in customers:
            self._render_row(customer)

    def _render_row(self, customer):
        row = ctk.CTkButton(
            self.list_frame,
            fg_color=("gray92", "gray20"),
            hover_color=("gray85", "gray28"),
            text_color=("gray10", "gray90"),
            corner_radius=8,
            height=64,
            anchor="e",
            command=lambda: self._open_detail(customer),
        )
        row.pack(fill="x", pady=4)

        # Keep the database value untouched. Only the display text is RTL.
        name = rtl(customer["name"])
        phone = str(customer["phone"] or "")
        first_line = name
        if phone:
            first_line = f"{name}   |   {phone}"

        second_line = rtl(
            f"{customer['order_count']} أوردر   —   إجمالي {customer['total_spend']:,.2f}"
        )
        row.configure(
            text=f"{first_line}\n{second_line}",
            font=ctk.CTkFont(size=13),
        )

    def _open_detail(self, customer):
        history = db.get_customer_orders(customer["id"], limit=50)
        history_rows = [
            {"date_key": h["order_date"], "total": h["total"], "sub_key": h["order_status"]}
            for h in history
        ]
        PartyDetailDialog(
            self.winfo_toplevel(), customer, history_rows,
            {
                "title_prefix": rtl("كشف حساب"),
                "date_label": rtl("التاريخ"),
                "history_label": rtl("الأوردرات"),
                "sub_label": rtl("الحالة"),
            }
        )
