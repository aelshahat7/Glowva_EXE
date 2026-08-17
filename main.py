"""
Glowva ERP Desktop - Starter App
==================================
First working version: opens a real window, shows a sidebar (matching our
Sheets tabs), and a live Dashboard pulling from the SQLite database.
The other sections are placeholders for now - once you confirm this runs
correctly on your machine, we build out each screen one at a time,
exactly like we did with the spreadsheet.

Note on Arabic text: Tkinter doesn't auto-flip layout to RTL the way
Google Sheets does. Text is right-aligned where it matters, but the
overall panel layout - including the new top menu bar - may still read
left-to-right structurally rather than right-to-left. All labels
themselves are Arabic; tell me if the ordering looks backwards once you
see it running and I'll flip the insertion order.
"""

import tkinter as tk
import customtkinter as ctk
import database as db
from rtl import rtl
from views.orders_view import OrdersView
from views.purchases_view import PurchasesView
from views.products_view import ProductsView
from views.profit_payout_view import ProfitPayoutView
from views.customers_view import CustomersView
from views.suppliers_view import SuppliersView
from views.inventory_view import InventoryView

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

NAV_ITEMS = [
    ("Dashboard", "📊"),
    ("Orders", "🧾"),
    ("Purchases", "🛒"),
    ("Products", "📦"),
    ("Inventory", "📋"),
    ("Customers", "👥"),
    ("Suppliers", "🚚"),
    ("ProfitPayout", "💸"),
]

ARABIC_LABELS = {
    "Dashboard": "لوحة التحكم",
    "Orders": "الأوردرات",
    "Purchases": "المشتريات",
    "Products": "الأصناف",
    "Inventory": "المخزون",
    "Customers": "العملاء",
    "Suppliers": "الموردين",
    "ProfitPayout": "صرف الأرباح",
}


class GlowvaApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Glowva ERP")
        self.geometry("1100x700")
        self.minsize(900, 600)

        db.init_db()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        self.grid_rowconfigure(0, weight=0)  # الشريط العلوي
        self.grid_rowconfigure(1, weight=1)  # محتوى البرنامج

        self._build_menu_bar()
        self._build_sidebar()
        self._build_content_area()

    def _build_menu_bar(self):

            self.topbar = ctk.CTkFrame(
                self,
                height=52,
                corner_radius=0,
                fg_color=("white", "gray15")
            )

            self.topbar.grid(
                row=0,
                column=0,
                columnspan=2,
                sticky="ew"
            )

            self.topbar.grid_propagate(False)

            # القوائم: أول عنصر يظهر أقصى اليمين
            menu_items = [
                (
                    "الرئيسية",
                    [
                        ("لوحة التحكم", lambda: self.navigate("Dashboard"))
                    ]
                ),
                (
                    "المبيعات",
                    [
                        ("الأوردرات", lambda: self.navigate("Orders"))
                    ]
                ),
                (
                    "المشتريات",
                    [
                        ("المشتريات", lambda: self.navigate("Purchases"))
                    ]
                ),
                (
                    "الأصناف والمخزون",
                    [
                        ("الأصناف", lambda: self.navigate("Products")),
                        ("المخزون", lambda: self.navigate("Inventory"))
                    ]
                ),
                (
                    "الموردون",
                    [
                        ("الموردون", lambda: self.navigate("Suppliers"))
                    ]
                ),
                (
                    "العملاء",
                    [
                        ("العملاء", lambda: self.navigate("Customers"))
                    ]
                ),
                (
                    "الحسابات",
                    [
                        ("صرف الأرباح", lambda: self.navigate("ProfitPayout"))
                    ]
                ),
            ]

            for title, items in menu_items:

                btn = ctk.CTkButton(
                    self.topbar,
                    text=rtl(title) + "  ▾",
                    width=125,
                    height=34,
                    corner_radius=6,
                    fg_color="transparent",
                    hover_color=("gray85", "gray25"),
                    text_color=("gray15", "gray90"),
                    font=ctk.CTkFont(size=13),
                    command=lambda t=title, i=items: self._show_dropdown(t, i)
                )

                # أول زر يمين، والباقي يتجه لليسار
                btn.pack(
                    side="right",
                    padx=2,
                    pady=9
                )

    def _show_dropdown(self, title, items):

        # إغلاق أي قائمة مفتوحة
        if hasattr(self, "_active_dropdown"):
            try:
                self._active_dropdown.destroy()
            except:
                pass

        # نافذة القائمة
        dropdown = ctk.CTkToplevel(self)
        self._active_dropdown = dropdown

        dropdown.overrideredirect(True)
        dropdown.resizable(False, False)

        frame = ctk.CTkFrame(
            dropdown,
            corner_radius=8,
            fg_color=("white", "gray20"),
            border_width=1,
            border_color=("gray80", "gray30")
        )

        frame.pack(
            fill="both",
            expand=True
        )

        for text, command in items:

            btn = ctk.CTkButton(
                frame,
                text=rtl(text),
                width=190,
                height=38,
                corner_radius=0,
                fg_color="transparent",
                hover_color=("gray90", "gray25"),
                text_color=("gray15", "gray90"),
                anchor="e",
                font=ctk.CTkFont(size=13),
                command=lambda c=command: self._close_dropdown_and_run(
                    dropdown,
                    c
                )
            )

            btn.pack(
                fill="x",
                padx=4,
                pady=2
            )

        # مكان القائمة تحت الشريط العلوي
        self.update_idletasks()

        x = self.winfo_pointerx()
        y = self.winfo_rooty() + 52

        dropdown.geometry(
            f"+{x - 190}+{y}"
        )

        dropdown.focus_force()

        dropdown.bind(
            "<FocusOut>",
            lambda e: self._close_dropdown(dropdown)
        )

    def _close_dropdown_and_run(self, dropdown, command):

        try:
            dropdown.destroy()
        except:
            pass

        command()

    def _close_dropdown(self, dropdown):

        try:
            dropdown.destroy()
        except:
            pass
            
    def _build_sidebar(self):

        sidebar = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0
        )

        # الشريط على اليمين
        sidebar.grid(
        row=1,
        column=1,
        sticky="nsew"

        )

        sidebar.grid_columnconfigure(
            0,
            weight=1
        )

        sidebar.grid_rowconfigure(
            len(NAV_ITEMS) + 1,
            weight=1
        )

        title = ctk.CTkLabel(
            sidebar,
            text="Glowva ERP",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            ),
            anchor="e"
        )

        title.grid(
            row=0,
            column=0,
            padx=20,
            pady=(20, 30),
            sticky="e"
        )

        self.nav_buttons = {}

        for i, (key, icon) in enumerate(
            NAV_ITEMS,
            start=1
        ):

            label = f"{icon}  {ARABIC_LABELS[key]}"

            btn = ctk.CTkButton(
                sidebar,
                text=label,
                anchor="e",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray30"),
                font=ctk.CTkFont(size=14),
                command=lambda k=key: self.navigate(k)
            )

            btn.grid(
                row=i,
                column=0,
                padx=15,
                pady=4,
                sticky="ew"
            )

            self.nav_buttons[key] = btn

    def _build_content_area(self):

        self.content = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=("gray95", "gray10")
        )

        # المحتوى على الشمال
        self.content.grid(
        row=1,
        column=0,
        sticky="nsew"
        )

        self.content.grid_columnconfigure(
            0,
            weight=1
        )

    def _clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def navigate(self, key):
        for k, btn in self.nav_buttons.items():
            btn.configure(fg_color="#1f6aa5" if k == key else "transparent")

        if key == "Dashboard":
            self.show_dashboard()
        elif key == "Orders":
            self.show_orders()
        elif key == "Purchases":
            self.show_purchases()
        elif key == "Products":
            self.show_products()
        elif key == "ProfitPayout":
            self.show_profit_payout()
        elif key == "Customers":
            self.show_customers()
        elif key == "Suppliers":
            self.show_suppliers()
        elif key == "Inventory":
            self.show_inventory()
        else:
            self.show_placeholder(key)

    def show_orders(self):
        self._clear_content()
        self.nav_buttons["Orders"].configure(fg_color="#1f6aa5")
        view = OrdersView(self.content)
        view.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)

    def show_purchases(self):
        self._clear_content()
        self.nav_buttons["Purchases"].configure(fg_color="#1f6aa5")
        view = PurchasesView(self.content)
        view.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)

    def show_products(self):
        self._clear_content()
        self.nav_buttons["Products"].configure(fg_color="#1f6aa5")
        view = ProductsView(self.content)
        view.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)

    def show_profit_payout(self):
        self._clear_content()
        self.nav_buttons["ProfitPayout"].configure(fg_color="#1f6aa5")
        view = ProfitPayoutView(self.content)
        view.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)

    def show_customers(self):
        self._clear_content()
        self.nav_buttons["Customers"].configure(fg_color="#1f6aa5")
        view = CustomersView(self.content)
        view.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)

    def show_suppliers(self):
        self._clear_content()
        self.nav_buttons["Suppliers"].configure(fg_color="#1f6aa5")
        view = SuppliersView(self.content)
        view.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)

    def show_inventory(self):
        self._clear_content()
        self.nav_buttons["Inventory"].configure(fg_color="#1f6aa5")
        view = InventoryView(self.content)
        view.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)

    def show_placeholder(self, key):
        self._clear_content()
        label = ctk.CTkLabel(
            self.content,
            text=f"{ARABIC_LABELS[key]}\n\nقريباً — الشاشة دي هنبنيها في الخطوة الجاية",
            font=ctk.CTkFont(size=18),
            justify="center"
        )
        label.grid(row=0, column=0, padx=40, pady=200)

    def show_dashboard(self):
        self._clear_content()
        self.nav_buttons["Dashboard"].configure(fg_color="#1f6aa5")

        header = ctk.CTkLabel(
            self.content, text="لوحة التحكم",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, padx=30, pady=(25, 15), sticky="w")

        summary = db.get_dashboard_summary()

        cards_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        cards_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        for i in range(3):
            cards_frame.grid_columnconfigure(i, weight=1)

        cards = [
            ("إجمالي المبيعات", f"{summary['total_sales']:,.2f}", "#2F5496"),
            ("إجمالي المشتريات", f"{summary['total_purchases']:,.2f}", "#2F5496"),
            ("صافي الربح التقديري", f"{summary['profit']:,.2f}", "#2F5496"),
            ("نسبة الربح", f"{summary['margin']*100:,.1f}%", "#2F5496"),
            ("أصناف قرّبت تخلص", f"{summary['low_stock_count']}",
             "#C0392B" if summary['low_stock_count'] > 0 else "#2F5496"),
            ("عدد الأوردرات", f"{summary['order_count']}", "#2F5496"),
            ("إجمالي صرف الأرباح", f"{summary['total_payouts']:,.2f}", "#E67E22"),
            ("المتاح فعليًا", f"{summary['available_balance']:,.2f}",
             "#C0392B" if summary['available_balance'] < 0 else "#27AE60"),
        ]

        for i, (label_text, value_text, color) in enumerate(cards):
            card = ctk.CTkFrame(cards_frame, corner_radius=10)
            card.grid(row=i // 3, column=i % 3, padx=8, pady=8, sticky="nsew")

            ctk.CTkLabel(card, text=label_text, font=ctk.CTkFont(size=13),
                         text_color="gray50").pack(padx=15, pady=(15, 2), anchor="e")
            ctk.CTkLabel(card, text=value_text, font=ctk.CTkFont(size=22, weight="bold"),
                         text_color=color).pack(padx=15, pady=(0, 15), anchor="e")

        if summary['low_stock_count'] > 0:
            low_items = db.get_low_stock()
            warn_frame = ctk.CTkFrame(self.content, corner_radius=10, fg_color="#FDECEA")
            warn_frame.grid(row=2, column=0, padx=30, pady=20, sticky="ew")
            ctk.CTkLabel(
                warn_frame, text="⚠️ أصناف قرّبت تخلص",
                font=ctk.CTkFont(size=15, weight="bold"), text_color="#C0392B"
            ).pack(padx=15, pady=(12, 5), anchor="e")
            for item in low_items[:5]:
                ctk.CTkLabel(
                    warn_frame,
                    text=f"• {item['product_name']} (المتبقي: {item['current_stock']:.0f})",
                    text_color="#C0392B"
                ).pack(padx=25, pady=2, anchor="e")
            warn_frame.pack_slaves()[-1].pack(pady=(2, 12))


if __name__ == "__main__":
    app = GlowvaApp()
    app.mainloop()
