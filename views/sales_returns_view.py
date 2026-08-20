import customtkinter as ctk
from datetime import date
import database as db
from rtl import rtl
from services import returns_service as rs


class SalesReturnsView(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        rs.initialize_returns()
        self.title("Glowva ERP - مرتجعات المبيعات")
        self.geometry("1000x650")
        self.minsize(850, 550)
        self.transient(parent)

        self.customer_map = {}
        self.invoice_map = {}
        self.line_entries = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_invoice_selector()
        self._build_items_area()
        self._build_footer()
        self._load_customers()

    def _build_header(self):
        ctk.CTkLabel(
            self,
            text=rtl("مرتجعات المبيعات"),
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=25, pady=(20, 10), sticky="e")

    def _build_invoice_selector(self):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid(row=1, column=0, padx=25, pady=10, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            frame,
            text=rtl("العميل"),
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=4, padx=10, pady=10, sticky="e")

        self.customer_combo = ctk.CTkComboBox(
            frame,
            values=[],
            justify="right",
            width=240,
        )
        self.customer_combo.grid(row=0, column=3, padx=10, pady=10, sticky="ew")

        ctk.CTkButton(
            frame,
            text=rtl("بحث"),
            width=90,
            command=self._search_customer_invoices,
        ).grid(row=0, column=2, padx=10, pady=10)

        ctk.CTkLabel(
            frame,
            text=rtl("الفاتورة"),
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=1, column=4, padx=10, pady=10, sticky="e")

        self.invoice_combo = ctk.CTkComboBox(
            frame,
            values=[],
            justify="right",
            width=420,
        )
        self.invoice_combo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.invoice_combo.bind("<<ComboboxSelected>>", self._on_invoice_selected)

        ctk.CTkButton(
            frame,
            text=rtl("تحميل الفاتورة"),
            command=self._load_selected_invoice,
        ).grid(row=1, column=0, padx=10, pady=10)

        self.invoice_info = ctk.CTkLabel(
            frame,
            text=rtl("اختار العميل ثم اضغط بحث لعرض فواتيره"),
            text_color="gray50",
        )
        self.invoice_info.grid(
            row=2,
            column=0,
            columnspan=5,
            padx=10,
            pady=(0, 10),
            sticky="e",
        )

    def _build_items_area(self):
        self.items_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.items_frame.grid(row=2, column=0, padx=25, pady=10, sticky="nsew")
        for col in range(5):
            self.items_frame.grid_columnconfigure(col, weight=1)
        self.items_frame.grid_columnconfigure(4, weight=4)

    def _build_footer(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=3, column=0, padx=25, pady=(0, 20), sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        self.reason_entry = ctk.CTkEntry(
            frame,
            placeholder_text=rtl("سبب المرتجع (اختياري)"),
            justify="right",
        )
        self.reason_entry.grid(row=0, column=1, padx=10, sticky="ew")

        self.save_button = ctk.CTkButton(
            frame,
            text=rtl("حفظ مرتجع المبيعات"),
            fg_color="#C0392B",
            hover_color="#922B21",
            command=self._save,
        )
        self.save_button.grid(row=0, column=0, padx=10)

        self.status_label = ctk.CTkLabel(
            frame,
            text="",
            text_color="#C0392B",
            justify="right",
        )
        self.status_label.grid(
            row=1,
            column=0,
            columnspan=2,
            padx=10,
            pady=(8, 0),
            sticky="e",
        )

    def _load_customers(self):
        self.customer_map = {}
        values = []
        for customer in db.list_customers():
            name = customer["name"] or ""
            if not name:
                continue
            display = rtl(name)
            self.customer_map[display] = customer["id"]
            values.append(display)

        self.customer_combo.configure(values=values)
        self.customer_combo.set("")
        self.invoice_combo.configure(values=[])
        self.invoice_combo.set("")
        self._clear_items()

    def _search_customer_invoices(self):
        self.status_label.configure(text="")
        self.invoice_map = {}
        self.invoice_combo.configure(values=[])
        self.invoice_combo.set("")
        self._clear_items()

        customer_display = self.customer_combo.get().strip()
        customer_id = self.customer_map.get(customer_display)
        if not customer_id:
            self.invoice_info.configure(text=rtl("اختار العميل الأول"))
            return

        invoices = rs.list_sales_invoices(customer_id=customer_id)
        values = []
        for inv in invoices:
            label = rtl(
                f"فاتورة رقم {inv['id']} | التاريخ {inv['order_date']} | الإجمالي {inv['total']:,.2f}"
            )
            self.invoice_map[label] = inv["id"]
            values.append(label)

        self.invoice_combo.configure(values=values)
        if values:
            self.invoice_combo.set(values[0])
            self.invoice_info.configure(text=rtl(f"تم العثور على {len(values)} فاتورة للعميل"))
            self._load_selected_invoice()
        else:
            self.invoice_info.configure(text=rtl("مفيش فواتير متاحة للمرتجع للعميل ده"))

    def _on_invoice_selected(self, event=None):
        self._load_selected_invoice()

    def _load_selected_invoice(self):
        self.status_label.configure(text="")
        label = self.invoice_combo.get()
        order_id = self.invoice_map.get(label)
        if not order_id:
            return

        invoices = rs.list_sales_invoices(limit=1000)
        inv = next((x for x in invoices if x["id"] == order_id), None)
        if inv:
            self.invoice_info.configure(
                text=rtl(
                    f"العميل: {inv['customer_name']} | التاريخ: {inv['order_date']} | إجمالي الفاتورة: {inv['total']:,.2f}"
                )
            )
        self._render_items(order_id)

    def _clear_items(self):
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        self.line_entries.clear()

    def _render_items(self, order_id):
        self._clear_items()

        headers = [
            rtl("كمية المرتجع"),
            rtl("متاح للمرتجع"),
            rtl("الكمية الأصلية"),
            rtl("السعر"),
            rtl("الصنف"),
        ]

        for col, text in enumerate(headers):
            ctk.CTkLabel(
                self.items_frame,
                text=text,
                font=ctk.CTkFont(weight="bold"),
                anchor="e",
            ).grid(row=0, column=col, padx=8, pady=8, sticky="ew")

        for row_idx, item in enumerate(rs.get_sales_return_lines(order_id), start=1):
            values = [
                None,
                f"{item['available_quantity']:g}",
                f"{item['sold_quantity']:g}",
                f"{item['unit_price']:,.2f}",
                rtl(item["product_name"]),
            ]

            for col, value in enumerate(values):
                if value is None:
                    continue
                ctk.CTkLabel(
                    self.items_frame,
                    text=value,
                    anchor="e",
                ).grid(row=row_idx, column=col, padx=8, pady=5, sticky="ew")

            entry = ctk.CTkEntry(
                self.items_frame,
                width=110,
                justify="right",
            )
            entry.insert(0, "0")
            entry.grid(row=row_idx, column=0, padx=8, pady=5, sticky="ew")
            self.line_entries[item["order_item_id"]] = {
                "entry": entry,
                "available": item["available_quantity"],
            }

    def _save(self):
        self.status_label.configure(text="")
        label = self.invoice_combo.get()
        order_id = self.invoice_map.get(label)
        if not order_id:
            self.status_label.configure(text=rtl("اختار فاتورة الأول"))
            return

        items = []
        for order_item_id, data in self.line_entries.items():
            try:
                qty = float(data["entry"].get() or 0)
            except ValueError:
                qty = 0

            if qty < 0 or qty > float(data["available"]) + 1e-9:
                self.status_label.configure(text=rtl("فيه كمية مرتجع غير صحيحة"))
                return

            if qty > 0:
                items.append({"order_item_id": order_item_id, "quantity": qty})

        try:
            rs.create_sales_return(
                order_id,
                items,
                reason=self.reason_entry.get().strip(),
                return_date=date.today().isoformat(),
            )
        except Exception as exc:
            self.status_label.configure(text=rtl(str(exc)))
            return

        self.reason_entry.delete(0, "end")
        self._search_customer_invoices()
        self.status_label.configure(
            text=rtl("تم حفظ مرتجع المبيعات وتحديث المخزون والحسابات"),
            text_color="#27AE60",
        )
