"""
Orders screen - the daily "checkout counter" of the app.
Pick a customer, add product lines one at a time (only in-stock products
are offered, mirroring the Sheets version), save the whole order as one
transaction, see it appear immediately in the recent-orders list.
"""

import customtkinter as ctk
from datetime import date
import database as db
from rtl import rtl, unrtl, contains_arabic
from views.product_search_dialog import ProductSearchDialog

# delete-button / total / price / quantity / product name
# Physical order is LTR so the product appears on the right and total on the left.
CART_COLUMN_WEIGHTS = (0, 1, 1, 1, 3)


class OrdersView(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.cart = []  # [{product_name, quantity, unit_price}, ...]

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._refresh_recent_orders()

    def _build_header(self):
        header = ctk.CTkLabel(
            self, text=rtl("الأوردرات"), font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, padx=30, pady=(25, 15), sticky="e")

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="nsew")
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        self._build_recent_panel(body)
        self._build_form(body)

    # ---------------- New order form ----------------

    def _build_form(self, parent):
        form = ctk.CTkScrollableFrame(parent, corner_radius=10)
        form.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=0)
        form.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(
            form, text=rtl("أوردر جديد"), font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=1, columnspan=2, padx=10, pady=(10, 15), sticky="e")

        r = 1
        ctk.CTkLabel(form, text=rtl("التاريخ")).grid(row=r, column=1, padx=10, pady=6, sticky="e")
        self.date_entry = ctk.CTkEntry(form, justify="right")
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.grid(row=r, column=0, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(form, text=rtl("اسم العميل")).grid(row=r, column=1, padx=10, pady=6, sticky="e")
        self.customer_combo = ctk.CTkComboBox(
            form, values=self._customer_names(), justify="right"
        )
        self.customer_combo.set("")
        self.customer_combo.grid(row=r, column=0, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(form, text=rtl("رقم الموبايل")).grid(row=r, column=1, padx=10, pady=6, sticky="e")
        self.phone_entry = ctk.CTkEntry(form, justify="right")
        self.phone_entry.grid(row=r, column=0, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkFrame(form, height=2, fg_color=("gray80", "gray30")).grid(
            row=r, column=1, columnspan=2, sticky="ew", padx=10, pady=12)

        r += 1
        ctk.CTkLabel(
            form, text=rtl("إضافة صنف للفاتورة"), font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=r, column=1, columnspan=2, padx=10, pady=(0, 8), sticky="e")

        r += 1
        ctk.CTkLabel(form, text=rtl("الصنف")).grid(row=r, column=1, padx=10, pady=6, sticky="e")
        product_row = ctk.CTkFrame(form, fg_color="transparent")
        product_row.grid(row=r, column=0, padx=10, pady=6, sticky="ew")
        product_row.grid_columnconfigure(0, weight=1)
        product_row.grid_columnconfigure(1, weight=0)

        self.product_entry = ctk.CTkEntry(
            product_row, placeholder_text=rtl("اكتبي اسم الصنف أو دوّري بـ🔍"), justify="right"
        )
        self.product_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            product_row, text="🔍", width=36, command=self._open_search
        ).grid(row=0, column=1, padx=(6, 0))

        r += 1
        ctk.CTkLabel(form, text=rtl("الكمية")).grid(row=r, column=1, padx=10, pady=6, sticky="e")
        self.qty_entry = ctk.CTkEntry(form, justify="right")
        self.qty_entry.insert(0, "1")
        self.qty_entry.grid(row=r, column=0, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(form, text=rtl("سعر الوحدة")).grid(row=r, column=1, padx=10, pady=6, sticky="e")
        self.price_entry = ctk.CTkEntry(form, justify="right")
        self.price_entry.grid(row=r, column=0, padx=10, pady=6, sticky="ew")

        r += 1
        self.line_error = ctk.CTkLabel(form, text="", text_color="#C0392B")
        self.line_error.grid(row=r, column=1, columnspan=2, padx=10, sticky="e")

        r += 1
        ctk.CTkButton(form, text=rtl("اضف للفاتورة"), command=self._add_line).grid(
            row=r, column=1, columnspan=2, padx=10, pady=(4, 10), sticky="ew")

        r += 1
        # Full-width invoice/cart inside the form.
        cart_container = ctk.CTkFrame(form, fg_color=("gray92", "gray17"), corner_radius=8)
        cart_container.grid(row=r, column=0, columnspan=3, padx=10, pady=6, sticky="ew")
        cart_container.grid_columnconfigure(0, weight=1)

        self.cart_header = ctk.CTkFrame(
            cart_container, fg_color=("gray85", "gray22"), corner_radius=6
        )
        self.cart_header.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        for col, weight in enumerate(CART_COLUMN_WEIGHTS):
            self.cart_header.grid_columnconfigure(col, weight=weight)
        for col, text in enumerate([
            "", rtl("الإجمالي"), rtl("السعر"), rtl("الكمية"), rtl("الصنف")
        ]):
            ctk.CTkLabel(
                self.cart_header, text=text, font=ctk.CTkFont(size=11, weight="bold"), anchor="e"
            ).grid(row=0, column=col, padx=6, pady=4, sticky="ew")

        self.cart_frame = ctk.CTkFrame(cart_container, fg_color="transparent")
        self.cart_frame.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        for col, weight in enumerate(CART_COLUMN_WEIGHTS):
            self.cart_frame.grid_columnconfigure(col, weight=weight)

        r += 1
        self.total_label = ctk.CTkLabel(
            form, text=rtl("الإجمالي: 0.00"), font=ctk.CTkFont(size=17, weight="bold")
        )
        self.total_label.grid(row=r, column=1, columnspan=2, padx=10, pady=(10, 6))

        r += 1
        ctk.CTkLabel(form, text=rtl("الخصم")).grid(row=r, column=1, padx=10, pady=6, sticky="e")
        self.discount_entry = ctk.CTkEntry(form, justify="right")
        self.discount_entry.insert(0, "0")
        self.discount_entry.grid(row=r, column=0, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(form, text=rtl("حالة الدفع")).grid(row=r, column=0, padx=10, pady=6, sticky="e")
        self.payment_combo = ctk.CTkComboBox(
            form, values=[rtl("مدفوع"), rtl("جزء مدفوع"), rtl("لسه لم يدفع")], justify="right"
        )
        self.payment_combo.grid(row=r, column=0, padx=10, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(form, text=rtl("حالة الطلب")).grid(row=r, column=1, padx=10, pady=6, sticky="e")
        self.status_combo = ctk.CTkComboBox(
            form, values=[rtl("تم التسليم"), rtl("قيد التنفيذ"), rtl("ملغي")], justify="right"
        )
        self.status_combo.grid(row=r, column=0, padx=10, pady=6, sticky="ew")

        r += 1
        self.save_error = ctk.CTkLabel(form, text="", text_color="#C0392B")
        self.save_error.grid(row=r, column=1, columnspan=2, padx=10, sticky="e")

        r += 1
        ctk.CTkButton(
            form, text="احفظ الفاتورة", fg_color="#27AE60", hover_color="#1E8449",
            font=ctk.CTkFont(size=14, weight="bold"), height=38,
            command=self._save_order
        ).grid(row=r, column=1, columnspan=2, padx=10, pady=(10, 15), sticky="ew")

    def _customer_names(self):
        # Display customer names in RTL while keeping the database value unchanged.
        return [rtl(c["name"]) for c in db.list_customers()]

    def _customer_name_from_display(self, value):
        value = unrtl(value).strip()
        if contains_arabic(value):
            return " ".join(reversed(value.split()))
        return value

    def _open_search(self):
        products = db.list_products()
        ProductSearchDialog(
            self.winfo_toplevel(), products, self._on_product_picked,
            subtitle_key="current_stock", subtitle_label=rtl("المتاح بالمخزون")
        )

    def _on_product_picked(self, product):
        self.product_entry.delete(0, "end")
        self.product_entry.insert(0, product["name"])

        self.price_entry.delete(0, "end")
        self.price_entry.insert(0, f"{product['sell_price']:g}")

    def _add_line(self):
        self.line_error.configure(text="")
        product = self.product_entry.get().strip()

        if not product:
            self.line_error.configure(text=rtl("اختاري صنف الأول"))
            return

        try:
            qty = float(self.qty_entry.get())
            price = float(self.price_entry.get())
        except ValueError:
            self.line_error.configure(text=rtl("الكمية والسعر لازم يكونوا أرقام"))
            return

        if qty <= 0:
            self.line_error.configure(text=rtl("الكمية لازم تكون أكبر من صفر"))
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
            self.cart_header.grid_remove()
            ctk.CTkLabel(
                self.cart_frame, text=rtl("لسه مفيش أصناف مضافة"), text_color="gray50"
            ).grid(row=0, column=0, columnspan=len(CART_COLUMN_WEIGHTS), padx=10, pady=10)
            self._update_total(0)
            return

        self.cart_header.grid()

        subtotal = 0
        for i, item in enumerate(self.cart):
            line_total = item["quantity"] * item["unit_price"]
            subtotal += line_total

            bg = ("gray95", "gray14") if i % 2 == 0 else ("gray90", "gray17")

            ctk.CTkButton(
                self.cart_frame, text="✕", width=26, height=26,
                fg_color="#C0392B", hover_color="#922B21",
                command=lambda idx=i: self._remove_line(idx)
            ).grid(row=i, column=0, padx=(0, 6), pady=2)

            # Physical order: delete | total | price | quantity | product.
            values = [
                f"{line_total:,.2f}",
                f"{item['unit_price']:,.2f}",
                f"{item['quantity']:g}",
                item["product_name"],
            ]
            for col, text in enumerate(values, start=1):
                ctk.CTkLabel(
                    self.cart_frame, text=text, anchor="e", fg_color=bg, font=ctk.CTkFont(size=12)
                ).grid(row=i, column=col, padx=6, pady=2, sticky="ew")

        self._update_total(subtotal)

    def _update_total(self, subtotal):
        try:
            discount = float(self.discount_entry.get() or 0)
        except ValueError:
            discount = 0
        self.total_label.configure(text=rtl(f"الإجمالي: {subtotal - discount:,.2f}"))

    def _remove_line(self, index):
        del self.cart[index]
        self._render_cart()

    def _save_order(self):
        self.save_error.configure(text="")

        if not self.cart:
            self.save_error.configure(text=rtl("لازم تضيفي صنف واحد على الأقل"))
            return

        customer = self._customer_name_from_display(self.customer_combo.get())
        if not customer:
            self.save_error.configure(text=rtl("لازم تكتبي اسم العميل"))
            return

        try:
            discount = float(self.discount_entry.get() or 0)
        except ValueError:
            discount = 0

        db.create_order(
            order_date=self.date_entry.get().strip() or date.today().isoformat(),
            customer_name=customer,
            items=self.cart,
            customer_phone=self.phone_entry.get().strip(),
            payment_status=unrtl(self.payment_combo.get()) or "مدفوع",
            order_status=unrtl(self.status_combo.get()) or "قيد التنفيذ",
            discount=discount,
        )

        self.cart = []
        self._render_cart()
        self.customer_combo.set("")
        self.customer_combo.configure(values=self._customer_names())
        self.phone_entry.delete(0, "end")
        self.discount_entry.delete(0, "end")
        self.discount_entry.insert(0, "0")

        self._refresh_recent_orders()

    # ---------------- Recent orders panel ----------------

    def _build_recent_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=10)
        panel.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            panel, text=rtl("آخر الأوردرات"), font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=15, pady=(15, 10), anchor="e")

        self.recent_frame = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.recent_frame.pack(fill="both", expand=True, padx=10, pady=(0, 15))

    def _refresh_recent_orders(self):
        for widget in self.recent_frame.winfo_children():
            widget.destroy()

        orders = db.list_recent_orders(limit=20)

        if not orders:
            ctk.CTkLabel(self.recent_frame, text=rtl("مفيش أوردرات لسه"), text_color="gray50").pack(pady=20)
            return

        status_colors = {
            "تم التسليم": "#27AE60",
            "قيد التنفيذ": "#E67E22",
            "ملغي": "#C0392B",
        }

        for o in orders:
            row = ctk.CTkFrame(self.recent_frame, fg_color=("gray92", "gray20"), corner_radius=8)
            row.pack(fill="x", pady=4)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(8, 0))
            ctk.CTkLabel(
                top, text=rtl(o["customer_name"]) if o["customer_name"] else rtl("بدون اسم"),
                font=ctk.CTkFont(weight="bold")
            ).pack(side="right")
            ctk.CTkLabel(
                top, text=f"{o['total']:,.2f}", font=ctk.CTkFont(weight="bold"),
                text_color="#2F5496"
            ).pack(side="left")

            bottom = ctk.CTkFrame(row, fg_color="transparent")
            bottom.pack(fill="x", padx=10, pady=(0, 8))
            ctk.CTkLabel(
                bottom, text=o["order_date"], text_color="gray50", font=ctk.CTkFont(size=11)
            ).pack(side="right")
            ctk.CTkLabel(
                bottom, text=rtl(o["order_status"]),
                text_color=status_colors.get(o["order_status"], "gray50"),
                font=ctk.CTkFont(size=11)
            ).pack(side="left")
