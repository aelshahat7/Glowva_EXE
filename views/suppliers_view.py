"""
Suppliers screen - mirrors Customers, but for the purchase side: who do
we buy from, how much total, and their full purchase history on click.
"""

import customtkinter as ctk
import database as db
from views.party_detail_dialog import PartyDetailDialog


class SuppliersView(ctk.CTkFrame):

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
            self, text="الموردين", font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=30, pady=(25, 10), sticky="w")

    def _build_search(self):
        self.search_entry = ctk.CTkEntry(
            self, placeholder_text="دوّري باسم المورد...", font=ctk.CTkFont(size=14)
        )
        self.search_entry.grid(row=1, column=0, padx=30, pady=(0, 15), sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_list())

    def _build_list_area(self):
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.grid(row=2, column=0, padx=30, pady=(0, 20), sticky="nsew")

    def _refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        suppliers = db.list_suppliers_with_stats()

        query = self.search_entry.get().strip().lower()
        if query:
            suppliers = [s for s in suppliers if query in s["name"].lower()]

        if not suppliers:
            ctk.CTkLabel(self.list_frame, text="مفيش موردين يطابقوا البحث", text_color="gray50").pack(pady=30)
            return

        for s in suppliers:
            self._render_row(s)

    def _render_row(self, supplier):
        row = ctk.CTkButton(
            self.list_frame, fg_color=("gray92", "gray20"), hover_color=("gray85", "gray28"),
            text_color=("gray10", "gray90"), corner_radius=8, height=64,
            anchor="e", command=lambda: self._open_detail(supplier)
        )
        row.pack(fill="x", pady=4)

        text = supplier["name"]
        if supplier["contact_info"]:
            text += f"   |   {supplier['contact_info']}"
        text += f"\n{supplier['purchase_count']} فاتورة توريد   —   إجمالي {supplier['total_purchased']:,.2f}"
        row.configure(text=text, font=ctk.CTkFont(size=13))

    def _open_detail(self, supplier):
        history = db.get_supplier_purchases(supplier["id"], limit=50)
        history_rows = [
            {"date_key": h["purchase_date"], "total": h["total"], "sub_key": h["invoice_number"]}
            for h in history
        ]
        PartyDetailDialog(
            self.winfo_toplevel(), supplier, history_rows,
            {
                "title_prefix": "كشف حساب",
                "date_label": "التاريخ",
                "history_label": "فواتير التوريد",
                "sub_label": "رقم الفاتورة",
            }
        )