import customtkinter as ctk
from datetime import date
from rtl import rtl
from services import returns_service as rs


class PurchaseReturnsView(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        rs.initialize_returns()
        self.title("Glowva ERP - مرتجعات المشتريات")
        self.geometry("1000x650")
        self.minsize(850, 550)
        self.transient(parent)

        self.supplier_map = {}
        self.invoice_map = {}
        self.line_entries = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._build_header()
        self._build_supplier_selector()
        self._build_invoice_selector()
        self._build_items_area()
        self._build_footer()
        self._load_suppliers()

    def _build_header(self):
        ctk.CTkLabel(
            self, text=rtl("مرتجعات المشتريات"),
            font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=25, pady=(20, 10), sticky="e")

    def _build_supplier_selector(self):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid(row=1, column=0, padx=25, pady=5, sticky="ew")
        frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            frame, text=rtl("اختار المورد"), font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=3, padx=10, pady=10, sticky="e")

        self.supplier_combo = ctk.CTkComboBox(
            frame, values=[], justify="right", width=420
        )
        self.supplier_combo.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        ctk.CTkButton(
            frame, text=rtl("بحث"), width=90, command=self._load_invoices
        ).grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkButton(
            frame, text=rtl("كل الموردين"), width=110,
            fg_color="gray55", hover_color="gray45",
            command=self._show_all_suppliers
        ).grid(row=0, column=0, padx=10, pady=10)

    def _build_invoice_selector(self):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid(row=2, column=0, padx=25, pady=5, sticky="ew")
        frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            frame, text=rtl("اختار فاتورة التوريد"),
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=3, padx=10, pady=10, sticky="e")

        self.invoice_combo = ctk.CTkComboBox(
            frame, values=[], justify="right", width=500
        )
        self.invoice_combo.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        self.invoice_combo.bind("<<ComboboxSelected>>", self._on_invoice_selected)

        ctk.CTkButton(
            frame, text=rtl("تحميل الفاتورة"),
            command=self._load_selected_invoice
        ).grid(row=0, column=1, padx=10, pady=10)

        self.invoice_info = ctk.CTkLabel(
            frame, text="", text_color="gray50", anchor="e"
        )
        self.invoice_info.grid(
            row=1, column=1, columnspan=3, padx=10, pady=(0, 10), sticky="ew"
        )

    def _build_items_area(self):
        self.items_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.items_frame.grid(row=3, column=0, padx=25, pady=10, sticky="nsew")
        self.items_frame.grid_columnconfigure(0, weight=1)

    def _build_footer(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=4, column=0, padx=25, pady=(0, 20), sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        self.reason_entry = ctk.CTkEntry(
            frame,
            placeholder_text=rtl("سبب المرتجع (اختياري)"),
            justify="right"
        )
        self.reason_entry.grid(row=0, column=1, padx=10, sticky="ew")

        self.save_button = ctk.CTkButton(
            frame,
            text=rtl("حفظ مرتجع المشتريات"),
            fg_color="#C0392B",
            hover_color="#922B21",
            command=self._save
        )
        self.save_button.grid(row=0, column=0, padx=10)

        self.status_label = ctk.CTkLabel(
            frame, text="", text_color="#C0392B"
        )
        self.status_label.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(8, 0), sticky="e"
        )

    def _load_suppliers(self):
        suppliers = rs.list_purchase_suppliers()
        self.supplier_map = {}
        values = []

        for supplier in suppliers:
            label = rtl(
                f"{supplier['name']} | {supplier['purchase_count']} فاتورة"
            )
            self.supplier_map[label] = supplier["id"]
            values.append(label)

        self.supplier_combo.configure(values=values)
        if values:
            self.supplier_combo.set(values[0])
        self._load_invoices()

    def _show_all_suppliers(self):
        self.supplier_combo.set("")
        self._load_invoices(show_all=True)

    def _selected_supplier_id(self):
        return self.supplier_map.get(self.supplier_combo.get())

    def _load_invoices(self, show_all=False):
        supplier_id = None if show_all else self._selected_supplier_id()
        invoices = rs.list_purchase_invoices(
            limit=5000, supplier_id=supplier_id
        )

        self.invoice_map = {}
        values = []

        for inv in invoices:
            invoice_no = inv["invoice_number"] or "-"
            label = rtl(
                f"فاتورة توريد {inv['id']} | {inv['supplier_name']} | "
                f"{inv['purchase_date']} | {invoice_no} | {inv['total']:,.2f}"
            )
            self.invoice_map[label] = inv["id"]
            values.append(label)

        self.invoice_combo.configure(values=values)
        self.invoice_combo.set(values[0] if values else "")

        if values:
            self._load_selected_invoice()
        else:
            self.invoice_info.configure(
                text=rtl("مفيش فواتير توريد للمورد المحدد")
            )
            self._clear_items()

    def _on_invoice_selected(self, event=None):
        self._load_selected_invoice()

    def _load_selected_invoice(self):
        self.status_label.configure(text="")
        label = self.invoice_combo.get()
        purchase_id = self.invoice_map.get(label)
        if not purchase_id:
            return

        invoices = {
            x["id"]: x
            for x in rs.list_purchase_invoices(limit=5000)
        }
        inv = invoices.get(purchase_id)
        if inv:
            self.invoice_info.configure(
                text=rtl(
                    f"المورد: {inv['supplier_name']} | "
                    f"التاريخ: {inv['purchase_date']} | "
                    f"رقم الفاتورة: {inv['invoice_number'] or '-'} | "
                    f"إجمالي الفاتورة: {inv['total']:,.2f}"
                )
            )

        self._render_items(purchase_id)

    def _clear_items(self):
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        self.line_entries.clear()

    def _render_items(self, purchase_id):
        self._clear_items()

        # RTL visual order: item on the far right, return quantity on the far left.
        headers = [
            rtl("الصنف"),
            rtl("السعر"),
            rtl("الكمية الأصلية"),
            rtl("متاح للمرتجع"),
            rtl("كمية المرتجع"),
        ]

        for col, text in enumerate(headers):
            weight = 5 if col == 0 else 1
            self.items_frame.grid_columnconfigure(
                col, weight=weight, uniform="return_cols"
            )
            ctk.CTkLabel(
                self.items_frame,
                text=text,
                font=ctk.CTkFont(weight="bold"),
                anchor="e"
            ).grid(
                row=0, column=col, padx=10, pady=10, sticky="ew"
            )

        for row_idx, item in enumerate(
            rs.get_purchase_return_lines(purchase_id), start=1
        ):
            values = [
                item["product_name"],
                f"{item['unit_price']:,.2f}",
                f"{item['purchased_quantity']:g}",
                f"{item['available_quantity']:g}",
            ]

            for col, value in enumerate(values):
                ctk.CTkLabel(
                    self.items_frame,
                    text=rtl(str(value)) if col == 0 else str(value),
                    anchor="e"
                ).grid(
                    row=row_idx, column=col, padx=10, pady=7, sticky="ew"
                )

            entry = ctk.CTkEntry(
                self.items_frame, width=120, justify="right"
            )
            entry.insert(0, "0")
            entry.grid(
                row=row_idx, column=4, padx=10, pady=7, sticky="ew"
            )

            self.line_entries[item["purchase_item_id"]] = {
                "entry": entry,
                "available": item["available_quantity"],
            }

    def _save(self):
        self.status_label.configure(text="")
        label = self.invoice_combo.get()
        purchase_id = self.invoice_map.get(label)

        if not purchase_id:
            self.status_label.configure(text=rtl("اختار فاتورة الأول"))
            return

        items = []
        for purchase_item_id, data in self.line_entries.items():
            try:
                qty = float(data["entry"].get() or 0)
            except ValueError:
                qty = 0

            if qty < 0 or qty > float(data["available"]) + 1e-9:
                self.status_label.configure(
                    text=rtl("فيه كمية مرتجع غير صحيحة")
                )
                return

            if qty > 0:
                items.append({
                    "purchase_item_id": purchase_item_id,
                    "quantity": qty
                })

        try:
            rs.create_purchase_return(
                purchase_id,
                items,
                reason=self.reason_entry.get().strip(),
                return_date=date.today().isoformat(),
            )
        except Exception as exc:
            self.status_label.configure(text=rtl(str(exc)))
            return

        self.reason_entry.delete(0, "end")
        self._load_invoices()
        self._load_selected_invoice()
        self.status_label.configure(
            text=rtl("تم حفظ مرتجع المشتريات وتحديث المخزون والحسابات"),
            text_color="#27AE60"
        )
