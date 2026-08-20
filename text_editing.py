"""Global text editing support for the Glowva ERP Tk/CustomTkinter UI."""

import tkinter as tk

_INSTALLED_INTERPRETERS = set()


def _is_editable(widget):
    """Return True when a widget accepts user edits."""
    try:
        state = widget.cget("state")
        return state not in ("disabled", "readonly")
    except (tk.TclError, AttributeError):
        return True


def _copy(event):
    try:
        event.widget.event_generate("<<Copy>>")
    except tk.TclError:
        pass
    return "break"


def _cut(event):
    widget = event.widget
    if _is_editable(widget):
        try:
            widget.event_generate("<<Cut>>")
        except tk.TclError:
            pass
    return "break"


def _paste(event):
    widget = event.widget
    if _is_editable(widget):
        try:
            widget.event_generate("<<Paste>>")
        except tk.TclError:
            pass
    return "break"


def _select_all(event):
    widget = event.widget
    try:
        if isinstance(widget, tk.Text):
            widget.tag_add(tk.SEL, "1.0", "end-1c")
            widget.mark_set(tk.INSERT, "end-1c")
            widget.see(tk.INSERT)
        else:
            widget.selection_range(0, "end")
            widget.icursor("end")
    except (tk.TclError, AttributeError):
        try:
            widget.event_generate("<<SelectAll>>")
        except tk.TclError:
            pass
    return "break"


def _show_context_menu(event):
    widget = event.widget

    menu = tk.Menu(widget, tearoff=0)

    menu.add_command(label="قص", command=lambda: _cut_from_menu(widget))
    menu.add_command(label="نسخ", command=lambda: _copy_from_menu(widget))
    menu.add_command(label="لصق", command=lambda: _paste_from_menu(widget))
    menu.add_separator()
    menu.add_command(label="تحديد الكل", command=lambda: _select_all_from_menu(widget))

    try:
        if not _has_selection(widget):
            menu.entryconfigure("قص", state="disabled")
            menu.entryconfigure("نسخ", state="disabled")
    except tk.TclError:
        pass

    if not _is_editable(widget):
        menu.entryconfigure("قص", state="disabled")
        menu.entryconfigure("لصق", state="disabled")

    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()

    return "break"


def _has_selection(widget):
    if isinstance(widget, tk.Text):
        try:
            return bool(widget.tag_ranges(tk.SEL))
        except tk.TclError:
            return False
    try:
        return bool(widget.selection_present())
    except (tk.TclError, AttributeError):
        return False


def _copy_from_menu(widget):
    try:
        widget.event_generate("<<Copy>>")
    except tk.TclError:
        pass


def _cut_from_menu(widget):
    if _is_editable(widget):
        try:
            widget.event_generate("<<Cut>>")
        except tk.TclError:
            pass


def _paste_from_menu(widget):
    if _is_editable(widget):
        try:
            widget.event_generate("<<Paste>>")
        except tk.TclError:
            pass


def _select_all_from_menu(widget):
    _select_all(type("Event", (), {"widget": widget})())


def install_text_editing(root):
    """Install global Cut/Copy/Paste/Select-All and context-menu support once."""
    try:
        tkapp = root.tk
    except AttributeError:
        return

    interpreter_id = str(tkapp)
    if interpreter_id in _INSTALLED_INTERPRETERS:
        return

    _INSTALLED_INTERPRETERS.add(interpreter_id)

    # Standard Tk Entry widgets are used inside CTkEntry/CTkComboBox.
    for widget_class in ("Entry", "Text"):
        root.bind_class(widget_class, "<Control-c>", _copy, add="+")
        root.bind_class(widget_class, "<Control-C>", _copy, add="+")
        root.bind_class(widget_class, "<Control-x>", _cut, add="+")
        root.bind_class(widget_class, "<Control-X>", _cut, add="+")
        root.bind_class(widget_class, "<Control-v>", _paste, add="+")
        root.bind_class(widget_class, "<Control-V>", _paste, add="+")
        root.bind_class(widget_class, "<Control-a>", _select_all, add="+")
        root.bind_class(widget_class, "<Control-A>", _select_all, add="+")
        root.bind_class(widget_class, "<Button-3>", _show_context_menu, add="+")

    # Linux/macOS-style alternate clipboard shortcut where supported.
    root.bind_class("Entry", "<Shift-Insert>", _paste, add="+")
    root.bind_class("Text", "<Shift-Insert>", _paste, add="+")
