"""
Shared detail popup: shows a customer or supplier's info plus their
transaction history. One dialog class, driven by config, so Customers
and Suppliers don't need two near-identical files.
"""

import customtkinter as ctk
from rtl import rtl, format_date


class PartyDetailDialog(ctk.CTkToplevel):

    def __init__(self, parent, party, history_rows, config):
        super().__init__(parent)

        self.title(f"{rtl(config['title_prefix'])}: {rtl(party['name'])}")
        self.geometry("480x560")
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header(party)
        self._build_summary(party, history_rows)
        self._build_history(history_rows, config)

    def _build_header(self, party):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        ctk.CTkLabel(
            header, text=rtl(party["name"]), font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="e")

        contact = party.get("phone") or party.get("contact_info")
        if contact:
            ctk.CTkLabel(
                header,
                text=str(contact),
                text_color="gray50",
                justify="right",
            ).pack(anchor="e")
        if party.get("address"):
            ctk.CTkLabel(
                header,
                text=rtl(party["address"]),
                text_color="gray50",
                justify="right",
            ).pack(anchor="e")

    def _build_summary(self, party, history_rows):
        total = sum(h["total"] for h in history_rows)
        count = len(history_rows)

        summary = ctk.CTkFrame(self, corner_radius=10)
        summary.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        summary.grid_columnconfigure((0, 1), weight=1)

        for i, (label, value) in enumerate([
            (rtl("الإجمالي"), f"{total:,.2f}"),
            (rtl("عدد العمليات"), str(count)),
        ]):
            box = ctk.CTkFrame(summary, fg_color="transparent")
            box.grid(row=0, column=i, padx=15, pady=15, sticky="ew")
            ctk.CTkLabel(
                box,
                text=label,
                text_color="gray50",
                font=ctk.CTkFont(size=12),
                justify="right",
            ).pack(anchor="e")
            ctk.CTkLabel(
                box,
                text=value,
                font=ctk.CTkFont(size=18, weight="bold"),
            ).pack(anchor="e")

    def _build_history(self, history_rows, config):
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            panel,
            text=rtl(config["history_label"]),
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="e", pady=(0, 8))

        if not history_rows:
            ctk.CTkLabel(
                panel,
                text=rtl("لسه مفيش عمليات"),
                text_color="gray50",
            ).grid(row=2, column=0, pady=30)
            return

        sub_label = rtl(config.get("sub_label", "تفاصيل"))
        column_weights = (1, 1, 2)

        header = ctk.CTkFrame(panel, fg_color=("gray85", "gray22"), corner_radius=6)
        header.grid(row=1, column=0, sticky="ew", pady=(0, 2))
        for col, weight in enumerate(column_weights):
            header.grid_columnconfigure(col, weight=weight)
        for col, text in enumerate([
            sub_label,
            rtl("الإجمالي"),
            rtl(config["date_label"]),
        ]):
            ctk.CTkLabel(
                header,
                text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="e",
            ).grid(row=0, column=col, padx=8, pady=6, sticky="ew")

        scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        scroll.grid(row=2, column=0, sticky="nsew")
        for col, weight in enumerate(column_weights):
            scroll.grid_columnconfigure(col, weight=weight)

        for row_index, h in enumerate(history_rows):
            bg = ("gray95", "gray14") if row_index % 2 == 0 else ("gray90", "gray17")
            sub_value = str(h.get("sub_key") or "—")
            if any("\u0600" <= ch <= "\u06ff" for ch in sub_value):
                sub_value = rtl(sub_value)

            values = [
                sub_value,
                f"{h['total']:,.2f}",
                format_date(h.get("date_key")),
            ]

            for col, text in enumerate(values):
                ctk.CTkLabel(
                    scroll,
                    text=text,
                    anchor="e",
                    fg_color=bg,
                    font=ctk.CTkFont(size=12),
                ).grid(row=row_index, column=col, padx=8, pady=4, sticky="ew")
