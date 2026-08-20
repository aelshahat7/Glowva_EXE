"""Small UI integration hook for the return windows."""

import customtkinter as ctk
from rtl import rtl


def install_return_buttons():
    from views.orders_view import OrdersView
    from views.purchases_view import PurchasesView
    from views.sales_returns_view import SalesReturnsView
    from views.purchase_returns_view import PurchaseReturnsView

    if not getattr(OrdersView, "_returns_hook_installed", False):
        original_orders_init = OrdersView.__init__

        def orders_init(self, parent):
            original_orders_init(self, parent)
            button = ctk.CTkButton(
                self,
                text=rtl("مرتجعات المبيعات"),
                width=130,
                height=30,
                fg_color="#C0392B",
                hover_color="#922B21",
                command=lambda: SalesReturnsView(self.winfo_toplevel()),
            )
            button.place(x=30, y=25)

        OrdersView.__init__ = orders_init
        OrdersView._returns_hook_installed = True

    if not getattr(PurchasesView, "_returns_hook_installed", False):
        original_purchases_init = PurchasesView.__init__

        def purchases_init(self, parent):
            original_purchases_init(self, parent)
            button = ctk.CTkButton(
                self,
                text=rtl("مرتجعات المشتريات"),
                width=130,
                height=30,
                fg_color="#C0392B",
                hover_color="#922B21",
                command=lambda: PurchaseReturnsView(self.winfo_toplevel()),
            )
            button.place(x=30, y=25)

        PurchasesView.__init__ = purchases_init
        PurchasesView._returns_hook_installed = True
