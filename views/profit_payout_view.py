"""
Profit Payout screen - log money taken out of the business for personal
use. Important distinction kept from the spreadsheet version: a payout
does NOT reduce business profit (that's a performance measure), it only
reduces the cash still available in the business.
"""

import customtkinter as ctk
from datetime import date
import database as db


class ProfitPayoutView(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_summary()
        self._build_body()
        self._refresh()

    def _build_header(self):
        ctk.CTkLabel(
            self, text="صرف الأرباح", font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, padx=30, pady=(25, 10), sticky="w")

    def _build_summary(self):
        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, padx=30, pady=(0, 15), sticky="ew")
        for i in range(3):
            self.summary_frame.grid_columnconfigure(i, weight=1)

    def _render_summary(self):
        for widget in self.summary_frame.winfo_children():
            widget.destroy()

        summary = db.get_dashboard_summary()

        cards = [
            ("الربح التقديري", summary["profit"], "#2F5496"),
            ("إجمالي المصروف", summary["total_payouts"], "#E67E22"),
            ("المتاح فعليًا", summary["available_balance"],
             "#C0392B" if summary["available_balance"] < 0 else "#27AE60"),
        ]

        for i, (label, value, color) in enumerate(cards):
            card = ctk.CTkFrame(self.summary_frame, corner_radius=10)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=13), text_color="gray50").pack(
                padx=15, pady=(15, 2), anchor="e")
            ctk.CTkLabel(
                card, text=f"{value:,.2f}", font=ctk.CTkFont(size=20, weight="bold"), text_color=color
            ).pack(padx=15, pady=(0, 15), anchor="e")

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, padx=30, pady=(0, 20), sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._build_form(body)
        self._build_history(body)

    def _build_form(self, parent):
        form = ctk.CTkFrame(parent, corner_radius=10)
        form.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            form, text="صرف جديد", font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 15), sticky="e")

        ctk.CTkLabel(form, text="التاريخ").grid(row=1, column=0, padx=15, pady=6, sticky="e")
        self.date_entry = ctk.CTkEntry(form)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.grid(row=1, column=1, padx=15, pady=6, sticky="ew")

        ctk.CTkLabel(form, text="المبلغ").grid(row=2, column=0, padx=15, pady=6, sticky="e")
        self.amount_entry = ctk.CTkEntry(form)
        self.amount_entry.grid(row=2, column=1, padx=15, pady=6, sticky="ew")

        ctk.CTkLabel(form, text="السبب").grid(row=3, column=0, padx=15, pady=6, sticky="e")
        self.reason_entry = ctk.CTkEntry(form, placeholder_text="اختياري")
        self.reason_entry.grid(row=3, column=1, padx=15, pady=6, sticky="ew")

        self.error_label = ctk.CTkLabel(form, text="", text_color="#C0392B")
        self.error_label.grid(row=4, column=0, columnspan=2, padx=15, pady=(6, 0), sticky="e")

        ctk.CTkButton(
            form, text="💾 سجّلي الصرف", fg_color="#27AE60", hover_color="#1E8449",
            font=ctk.CTkFont(size=14, weight="bold"), height=38,
            command=self._save
        ).grid(row=5, column=0, columnspan=2, padx=15, pady=(15, 15), sticky="ew")

    def _save(self):
        self.error_label.configure(text="")

        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            self.error_label.configure(text="المبلغ لازم يكون رقم")
            return

        if amount <= 0:
            self.error_label.configure(text="المبلغ لازم يكون أكبر من صفر")
            return

        db.add_profit_payout(
            payout_date=self.date_entry.get().strip() or date.today().isoformat(),
            amount=amount,
            reason=self.reason_entry.get().strip(),
        )

        self.amount_entry.delete(0, "end")
        self.reason_entry.delete(0, "end")
        self._refresh()

    def _build_history(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=10)
        panel.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            panel, text="آخر عمليات الصرف", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=15, pady=(15, 10), anchor="e")

        self.history_frame = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.history_frame.pack(fill="both", expand=True, padx=10, pady=(0, 15))

    def _refresh(self):
        self._render_summary()

        for widget in self.history_frame.winfo_children():
            widget.destroy()

        payouts = db.list_profit_payouts(limit=30)

        if not payouts:
            ctk.CTkLabel(self.history_frame, text="لسه مفيش عمليات صرف", text_color="gray50").pack(pady=20)
            return

        for p in payouts:
            row = ctk.CTkFrame(self.history_frame, fg_color=("gray92", "gray20"), corner_radius=8)
            row.pack(fill="x", pady=4)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(8, 0))
            ctk.CTkLabel(
                top, text=f"{p['amount']:,.2f}", font=ctk.CTkFont(weight="bold"), text_color="#E67E22"
            ).pack(side="left")
            ctk.CTkLabel(top, text=p["payout_date"], text_color="gray50", font=ctk.CTkFont(size=11)).pack(side="right")

            if p["reason"]:
                ctk.CTkLabel(
                    row, text=p["reason"], text_color="gray50", font=ctk.CTkFont(size=12)
                ).pack(anchor="e", padx=10, pady=(0, 8))
            else:
                ctk.CTkFrame(row, height=8, fg_color="transparent").pack()
