"""
Add/Edit product popup. Same dialog handles both cases:
product=None -> creating a brand new product
product={...} -> editing an existing one (id present)
"""

import sqlite3
import customtkinter as ctk
import database as db


class ProductEditDialog(ctk.CTkToplevel):

    def __init__(self, parent, product, on_saved):
        super().__init__(parent)

        self.product = product
        self.on_saved = on_saved
        is_new = product is None

        self.title("صنف جديد" if is_new else f"تعديل: {product['name']}")
        self.geometry("440x480")
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(1, weight=1)

        r = 0
        ctk.CTkLabel(
            self, text="صنف جديد" if is_new else "تعديل بيانات الصنف",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=r, column=0, columnspan=2, padx=15, pady=(15, 15), sticky="e")

        r += 1
        ctk.CTkLabel(self, text="الاسم *").grid(row=r, column=0, padx=15, pady=6, sticky="e")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.grid(row=r, column=1, padx=15, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(self, text="الفئة").grid(row=r, column=0, padx=15, pady=6, sticky="e")
        self.category_entry = ctk.CTkEntry(self)
        self.category_entry.grid(row=r, column=1, padx=15, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(self, text="سعر البيع").grid(row=r, column=0, padx=15, pady=6, sticky="e")
        self.sell_entry = ctk.CTkEntry(self)
        self.sell_entry.grid(row=r, column=1, padx=15, pady=6, sticky="ew")

        r += 1
        ctk.CTkLabel(self, text="سعر الشراء").grid(row=r, column=0, padx=15, pady=6, sticky="e")
        self.buy_entry = ctk.CTkEntry(self)
        self.buy_entry.grid(row=r, column=1, padx=15, pady=6, sticky="ew")

        r += 1
        label_text = "الرصيد الافتتاحي" if is_new else "تصحيح الرصيد الافتتاحي"
        ctk.CTkLabel(self, text=label_text).grid(row=r, column=0, padx=15, pady=6, sticky="e")
        self.opening_entry = ctk.CTkEntry(self)
        self.opening_entry.grid(row=r, column=1, padx=15, pady=6, sticky="ew")

        if not is_new:
            r += 1
            ctk.CTkLabel(
                self, text="(غيّريه بس لو عملتي جرد فعلي ولقيتي فرق)",
                text_color="gray50", font=ctk.CTkFont(size=11)
            ).grid(row=r, column=0, columnspan=2, padx=15, sticky="e")

        r += 1
        ctk.CTkLabel(self, text="حد التنبيه بالمخزون").grid(row=r, column=0, padx=15, pady=6, sticky="e")
        self.threshold_entry = ctk.CTkEntry(self)
        self.threshold_entry.grid(row=r, column=1, padx=15, pady=6, sticky="ew")

        r += 1
        self.error_label = ctk.CTkLabel(self, text="", text_color="#C0392B")
        self.error_label.grid(row=r, column=0, columnspan=2, padx=15, pady=(10, 0), sticky="e")

        r += 1
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=r, column=0, columnspan=2, padx=15, pady=20, sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btn_row, text="إلغاء", fg_color="gray50", hover_color="gray40",
                      command=self.destroy).grid(row=0, column=1, padx=(6, 0), sticky="ew")
        ctk.CTkButton(btn_row, text="💾 حفظ", fg_color="#27AE60", hover_color="#1E8449",
                      command=self._save).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._fill_fields()

    def _fill_fields(self):
        if self.product is None:
            self.opening_entry.insert(0, "0")
            self.threshold_entry.insert(0, "5")
            return

        p = self.product
        self.name_entry.insert(0, p["name"])
        self.category_entry.insert(0, p["category"] or "")
        self.sell_entry.insert(0, f"{p['sell_price']:g}")
        self.buy_entry.insert(0, f"{p['buy_price']:g}")
        self.opening_entry.insert(0, f"{p['opening_stock']:g}")
        self.threshold_entry.insert(0, f"{p['low_stock_threshold']:g}")

    def _save(self):
        self.error_label.configure(text="")

        name = self.name_entry.get().strip()
        if not name:
            self.error_label.configure(text="لازم تكتبي اسم الصنف")
            return

        try:
            sell = float(self.sell_entry.get() or 0)
            buy = float(self.buy_entry.get() or 0)
            opening = float(self.opening_entry.get() or 0)
            threshold = float(self.threshold_entry.get() or 5)
        except ValueError:
            self.error_label.configure(text="الأسعار والأرقام لازم تكون أرقام صحيحة")
            return

        category = self.category_entry.get().strip()

        try:
            if self.product is None:
                db.add_product(name, category, sell, buy, opening, threshold)
            else:
                db.update_product(self.product["id"], name, category, sell, buy, opening, threshold)
        except sqlite3.IntegrityError:
            self.error_label.configure(text="فيه صنف تاني بنفس الاسم بالظبط")
            return

        self.on_saved()
        self.destroy()
