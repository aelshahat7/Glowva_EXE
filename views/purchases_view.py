"""
Purchases screen - recording stock coming in from suppliers.
Same overall shape as Orders (form + cart + recent list), but the product
field now uses the search-popup pattern instead of a plain dropdown, and
typing a brand-new product name is always allowed (first-time purchases
are exactly how new products enter the system).
"""

import customtkinter as ctk
from datetime import date
import database as db
from views.product_search_dialog import ProductSearchDialog


class PurchasesView(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.cart = []  # [{product_name, quantity, unit_price}, ...]

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._refresh_recent_purchases()

    def _build_header(self):
        ctk.CTkLabel(
            self, text="المشتريات", font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=30, pady=(25, 15), sticky="w")

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._build_form(body)
        self._build_recent_panel(body)

    # ---------------- New purchase form ----------------

    def _build_form(self, parent):
        form = ctk.CTkScrollableFrame(parent, corner_radius=10)
        form.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            form, text="فاتورة توريد جديدة", font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 15), sticky="e")

        r = 1
        ctk.CTkLabel(form, text="التاريخ").grid(row=r, column=0, padx=10, pady=6, sticky="e")
        self.date_entry = ctk.CTkEntry(form)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.grid(row=r, column=1, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(form, text="المورد").grid(row=r, column=0, padx=10, pady=6, sticky="e")
        self.supplier_combo = ctk.CTkComboBox(form, values=self._supplier_names())
        self.supplier_combo.set("")
        self.supplier_combo.grid(row=r, column=1, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(form, text="رقم الفاتورة").grid(row=r, column=0, padx=10, pady=6, sticky="e")
        self.invoice_entry = ctk.CTkEntry(form)
        self.invoice_entry.grid(row=r, column=1, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkFrame(form, height=2, fg_color=("gray80", "gray30")).grid(
            row=r, column=0, columnspan=2, sticky="ew", padx=10, pady=12)

        r += 1
        ctk.CTkLabel(
            form, text="إضافة صنف", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=r, column=0, columnspan=2, padx=10, pady=(0, 8), sticky="e")

        r += 1
        ctk.CTkLabel(form, text="الصنف").grid(row=r, column=0, padx=10, pady=6, sticky="e")
        product_row = ctk.CTkFrame(form, fg_color="transparent")
        product_row.grid(row=r, column=1, padx=10, pady=6, sticky="ew")
        product_row.grid_columnconfigure(0, weight=1)

        self.product_entry = ctk.CTkEntry(
            product_row, placeholder_text="اكتبي اسم صنف جديد أو دوّري بـ🔍"
        )
        self.product_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            product_row, text="🔍", width=36, command=self._open_search
        ).grid(row=0, column=1, padx=(6, 0))

        r += 1
        ctk.CTkLabel(form, text="الكمية").grid(row=r, column=0, padx=10, pady=6, sticky="e")
        self.qty_entry = ctk.CTkEntry(form)
        self.qty_entry.insert(0, "1")
        self.qty_entry.grid(row=r, column=1, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(form, text="سعر الوحدة").grid(row=r, column=0, padx=10, pady=6, sticky="e")
        self.price_entry = ctk.CTkEntry(form)
        self.price_entry.grid(row=r, column=1, padx=10, pady=6, sticky="ew")

        r += 1
        self.line_error = ctk.CTkLabel(form, text="", text_color="#C0392B")
        self.line_error.grid(row=r, column=0, columnspan=2, padx=10, sticky="e")

        r += 1
        ctk.CTkButton(form, text="➕ أضيفي للفاتورة", command=self._add_line).grid(
            row=r, column=0, columnspan=2, padx=10, pady=(4, 10), sticky="ew")

        r += 1
        self.cart_frame = ctk.CTkFrame(form, fg_color=("gray92", "gray17"), corner_radius=8)
        self.cart_frame.grid(row=r, column=0, columnspan=2, padx=10, pady=6, sticky="ew")

        r += 1
        self.total_label = ctk.CTkLabel(
            form, text="الإجمالي: 0.00", font=ctk.CTkFont(size=17, weight="bold")
        )
        self.total_label.grid(row=r, column=0, columnspan=2, padx=10, pady=(10, 6))

        r += 1
        self.save_error = ctk.CTkLabel(form, text="", text_color="#C0392B")
        self.save_error.grid(row=r, column=0, columnspan=2, padx=10, sticky="e")

        r += 1
        ctk.CTkButton(
            form, text="💾 احفظي فاتورة التوريد", fg_color="#27AE60", hover_color="#1E8449",
            font=ctk.CTkFont(size=14, weight="bold"), height=38,
            command=self._save_purchase
        ).grid(row=r, column=0, columnspan=2, padx=10, pady=(10, 15), sticky="ew")

    def _supplier_names(self):
        return [s["name"] for s in db.list_suppliers()]

    def _open_search(self):
        products = db.list_products()
        ProductSearchDialog(
            self.winfo_toplevel(), products, self._on_product_picked,
            subtitle_key="buy_price", subtitle_label="آخر سعر شراء"
        )

    def _on_product_picked(self, product):
        self.product_entry.delete(0, "end")
        self.product_entry.insert(0, product["name"])

        last_price = db.get_last_purchase_price(product["name"])
        self.price_entry.delete(0, "end")
        self.price_entry.insert(0, f"{last_price:g}")

    def _add_line(self):
        self.line_error.configure(text="")
        product = self.product_entry.get().strip()

        if not product:
            self.line_error.configure(text="اكتبي اسم الصنف الأول")
            return

        try:
            qty = float(self.qty_entry.get())
            price = float(self.price_entry.get())
        except ValueError:
            self.line_error.configure(text="الكمية والسعر لازم يكونوا أرقام")
            return

        if qty <= 0:
            self.line_error.configure(text="الكمية لازم تكون أكبر من صفر")
            return

        self.cart.append({"product_name": product, "quantity": qty, "unit_price": price})
        self._render_cart()

        self.product_entry.delete(0, "end")
        self.qty_entry.delete(0, "end")
        self.qty_entry.insert(0, "1")
        self.price_entry.delete(0, "end")

    def _render_cart(self):
        for widget in self.cart_frame.winfo_children():
            widget.destroy()

        if not self.cart:
            ctk.CTkLabel(self.cart_frame, text="لسه مفيش أصناف مضافة", text_color="gray50").pack(
                padx=10, pady=10)

        total = 0
        for i, item in enumerate(self.cart):
            line_total = item["quantity"] * item["unit_price"]
            total += line_total

            row = ctk.CTkFrame(self.cart_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)

            ctk.CTkButton(
                row, text="✕", width=26, height=26, fg_color="#C0392B", hover_color="#922B21",
                command=lambda idx=i: self._remove_line(idx)
            ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                row, text=f"{item['product_name']}  ×{item['quantity']:g}  =  {line_total:,.2f}"
            ).pack(side="left")

        self.total_label.configure(text=f"الإجمالي: {total:,.2f}")

    def _remove_line(self, index):
        del self.cart[index]
        self._render_cart()

    def _save_purchase(self):
        self.save_error.configure(text="")

        if not self.cart:
            self.save_error.configure(text="لازم تضيفي صنف واحد على الأقل")
            return

        supplier = self.supplier_combo.get().strip()
        if not supplier:
            self.save_error.configure(text="لازم تكتبي اسم المورد")
            return

        db.create_purchase(
            purchase_date=self.date_entry.get().strip() or date.today().isoformat(),
            supplier_name=supplier,
            items=self.cart,
            invoice_number=self.invoice_entry.get().strip(),
        )

        self.cart = []
        self._render_cart()
        self.supplier_combo.set("")
        self.supplier_combo.configure(values=self._supplier_names())
        self.invoice_entry.delete(0, "end")

        self._refresh_recent_purchases()

    # ---------------- Recent purchases panel ----------------

    def _build_recent_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=10)
        panel.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            panel, text="آخر فواتير التوريد", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=15, pady=(15, 10), anchor="e")

        self.recent_frame = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.recent_frame.pack(fill="both", expand=True, padx=10, pady=(0, 15))

    def _refresh_recent_purchases(self):
        for widget in self.recent_frame.winfo_children():
            widget.destroy()

        purchases = db.list_recent_purchases(limit=20)

        if not purchases:
            ctk.CTkLabel(self.recent_frame, text="مفيش فواتير توريد لسه", text_color="gray50").pack(pady=20)
            return

        for p in purchases:
            row = ctk.CTkFrame(self.recent_frame, fg_color=("gray92", "gray20"), corner_radius=8)
            row.pack(fill="x", pady=4)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(8, 0))
            ctk.CTkLabel(
                top, text=p["supplier_name"] or "بدون اسم", font=ctk.CTkFont(weight="bold")
            ).pack(side="right")
            ctk.CTkLabel(
                top, text=f"{p['total']:,.2f}", font=ctk.CTkFont(weight="bold"),
                text_color="#2F5496"
            ).pack(side="left")

            bottom = ctk.CTkFrame(row, fg_color="transparent")
            bottom.pack(fill="x", padx=10, pady=(0, 8))
            ctk.CTkLabel(bottom, text=p["purchase_date"], text_color="gray50", font=ctk.CTkFont(size=11)).pack(side="right")
            if p["invoice_number"]:
                ctk.CTkLabel(bottom, text=f"# {p['invoice_number']}", text_color="gray50", font=ctk.CTkFont(size=11)).pack(side="left")
