import re
import tkinter as tk
from datetime import datetime, date, timedelta

RLE = "\u202B"
LRE = "\u202A"
PDF = "\u202C"


def contains_arabic(text):
    text = str(text or "")
    return any(
        "\u0600" <= ch <= "\u06FF"
        or "\u0750" <= ch <= "\u077F"
        or "\u08A0" <= ch <= "\u08FF"
        or "\uFB50" <= ch <= "\uFDFF"
        or "\uFE70" <= ch <= "\uFEFF"
        for ch in text
    )


def format_date(value):
    """Convert app/imported date values to DD/MM/YYYY for display."""
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    text = str(value).strip()
    if not text:
        return "—"

    try:
        serial = float(text.replace(",", ""))
        if 20000 <= serial <= 80000:
            base = datetime(1899, 12, 30)
            return (base + timedelta(days=serial)).strftime("%d/%m/%Y")
    except (TypeError, ValueError, OverflowError):
        pass

    formats = (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
    )

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return text


def rtl(text):
    if text is None:
        return ""
    text = str(text)
    if not text.strip():
        return ""
    if not contains_arabic(text):
        return text
    if not re.search(r"[A-Za-z0-9]", text):
        return " ".join(reversed(text.split()))
    parts = text.split()
    if len(parts) <= 1:
        return text
    return " ".join(reversed(parts))


def unrtl(text):
    if text is None:
        return ""
    return str(text).replace("\u200E", "").replace("\u200F", "").replace("\u202A", "").replace("\u202B", "").replace("\u202C", "").replace("\u202D", "").replace("\u202E", "")


# ==========================================================
# Global Cut / Copy / Paste for native Tk Entry/Text widgets
# ==========================================================

_context_menus = {}


def _is_editable(widget):
    try:
        return str(widget.cget("state")) != "disabled"
    except (tk.TclError, AttributeError):
        return True


def _select_all_widget(widget):
    if not _is_editable(widget):
        return "break"
    try:
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "end-1c")
        else:
            widget.selection_range(0, "end")
            widget.icursor("end")
        widget.focus_set()
    except tk.TclError:
        pass
    return "break"


def _copy_widget(widget):
    try:
        widget.event_generate("<<Copy>>")
    except tk.TclError:
        pass
    return "break"


def _cut_widget(widget):
    if not _is_editable(widget):
        return "break"
    try:
        widget.event_generate("<<Cut>>")
    except tk.TclError:
        pass
    return "break"


def _paste_widget(widget):
    if not _is_editable(widget):
        return "break"
    try:
        widget.event_generate("<<Paste>>")
    except tk.TclError:
        pass
    return "break"


def _has_selection(widget):
    try:
        if isinstance(widget, tk.Text):
            return bool(widget.tag_ranges("sel"))
        return bool(widget.selection_present())
    except tk.TclError:
        return False


def _show_context_menu(event):
    widget = event.widget
    if not isinstance(widget, (tk.Entry, tk.Text)) or not _is_editable(widget):
        return

    old = _context_menus.get(widget)
    if old is not None:
        try:
            old.destroy()
        except tk.TclError:
            pass

    menu = tk.Menu(widget, tearoff=False)
    _context_menus[widget] = menu
    selected = _has_selection(widget)

    menu.add_command(label="قص", state="normal" if selected else "disabled", command=lambda w=widget: _cut_widget(w))
    menu.add_command(label="نسخ", state="normal" if selected else "disabled", command=lambda w=widget: _copy_widget(w))
    menu.add_command(label="لصق", command=lambda w=widget: _paste_widget(w))
    menu.add_separator()
    menu.add_command(label="تحديد الكل", command=lambda w=widget: _select_all_widget(w))

    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()
    return "break"


_TEXT_EDIT_BINDINGS_INSTALLED = False


def _install_text_edit_bindings():
    global _TEXT_EDIT_BINDINGS_INSTALLED
    if _TEXT_EDIT_BINDINGS_INSTALLED:
        return

    tk.Entry.bind_class("Entry", "<Control-c>", lambda e: _copy_widget(e.widget), add="+")
    tk.Entry.bind_class("Entry", "<Control-x>", lambda e: _cut_widget(e.widget), add="+")
    tk.Entry.bind_class("Entry", "<Control-v>", lambda e: _paste_widget(e.widget), add="+")
    tk.Entry.bind_class("Entry", "<Control-a>", lambda e: _select_all_widget(e.widget), add="+")
    tk.Entry.bind_class("Entry", "<Button-3>", _show_context_menu, add="+")

    tk.Text.bind_class("Text", "<Control-c>", lambda e: _copy_widget(e.widget), add="+")
    tk.Text.bind_class("Text", "<Control-x>", lambda e: _cut_widget(e.widget), add="+")
    tk.Text.bind_class("Text", "<Control-v>", lambda e: _paste_widget(e.widget), add="+")
    tk.Text.bind_class("Text", "<Control-a>", lambda e: _select_all_widget(e.widget), add="+")
    tk.Text.bind_class("Text", "<Button-3>", _show_context_menu, add="+")

    _TEXT_EDIT_BINDINGS_INSTALLED = True


_install_text_edit_bindings()
