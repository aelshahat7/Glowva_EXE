"""Safe Arabic text direction + explicit RTL view mirroring.

This module does NOT patch grid(), pack(), or any Tk geometry method.
It only wraps Arabic text in Unicode RTL embedding controls and, for
screen/dialog classes, mirrors the completed layout once after mapping.
"""

import tkinter as tk
import customtkinter as ctk

RLE = "\u202B"  # Right-to-Left Embedding
PDF = "\u202C"  # Pop Directional Formatting

_ARABIC_RANGES = (
    ("\u0600", "\u06FF"),
    ("\u0750", "\u077F"),
    ("\u08A0", "\u08FF"),
    ("\uFB50", "\uFDFF"),
    ("\uFE70", "\uFEFF"),
)


def _contains_arabic(text):
    return any(
        start <= char <= end
        for char in text
        for start, end in _ARABIC_RANGES
    )


def rtl(text):
    """Return display-safe text without changing stored data."""
    if text is None:
        return ""

    text = str(text)

    if not text.strip() or not _contains_arabic(text):
        return text

    if text.startswith(RLE) and text.endswith(PDF):
        return text

    return f"{RLE}{text}{PDF}"


def unrtl(text):
    """Remove our invisible directional controls."""
    if text is None:
        return ""

    return str(text).replace(RLE, "").replace(PDF, "")


def _mirror_sticky(sticky):
    if not sticky:
        return sticky

    return str(sticky).translate(
        str.maketrans({"e": "w", "w": "e"})
    )


def _mirror_grid(parent):
    items = []

    for child in parent.winfo_children():
        try:
            info = child.grid_info()
        except Exception:
            continue

        if not info:
            continue

        try:
            col = int(info.get("column", 0))
            span = max(1, int(info.get("columnspan", 1)))
            row = int(info.get("row", 0))
            rowspan = max(1, int(info.get("rowspan", 1)))
            items.append((child, col, span, row, rowspan, info.get("sticky", "")))
        except (TypeError, ValueError):
            continue

    if not items:
        return

    max_col = max(col + span - 1 for _, col, span, _, _, _ in items)

    configs = {}
    for col in range(max_col + 1):
        try:
            cfg = parent.grid_columnconfigure(col)
            configs[col] = {
                "weight": cfg.get("weight", 0),
                "minsize": cfg.get("minsize", 0),
                "pad": cfg.get("pad", 0),
                "uniform": cfg.get("uniform", ""),
            }
        except Exception:
            configs[col] = {}

    for child, col, span, row, rowspan, sticky in items:
        new_col = max_col - col - span + 1
        try:
            child.grid_configure(
                row=row,
                column=new_col,
                rowspan=rowspan,
                columnspan=span,
                sticky=_mirror_sticky(sticky),
            )
        except Exception:
            pass

    for logical_col, cfg in configs.items():
        actual_col = max_col - logical_col
        try:
            parent.grid_columnconfigure(
                actual_col,
                weight=cfg.get("weight", 0),
                minsize=cfg.get("minsize", 0),
                pad=cfg.get("pad", 0),
                uniform=cfg.get("uniform", ""),
            )
        except Exception:
            pass


def _mirror_pack(parent):
    for child in parent.winfo_children():
        try:
            info = child.pack_info()
        except Exception:
            continue

        if not info:
            continue

        side = info.get("side")
        if side not in ("left", "right"):
            continue

        try:
            child.pack_configure(
                side="right" if side == "left" else "left"
            )
        except Exception:
            pass


def mirror_layout(root):
    """Mirror an already-built view/dialog recursively, once."""
    if root is None:
        return

    if getattr(root, "_glowva_rtl_applied", False):
        return

    root._glowva_rtl_applied = True

    _mirror_grid(root)
    _mirror_pack(root)

    for child in root.winfo_children():
        mirror_layout(child)


def _patch_text_widgets():
    """Patch only text properties, never geometry management."""
    if getattr(ctk, "_glowva_rtl_text_installed", False):
        return

    text_classes = [
        "CTkLabel",
        "CTkButton",
        "CTkCheckBox",
        "CTkRadioButton",
        "CTkSwitch",
        "CTkOptionMenu",
    ]

    for class_name in text_classes:
        cls = getattr(ctk, class_name, None)
        if cls is None:
            continue

        original_init = cls.__init__
        original_configure = getattr(cls, "configure", None)

        def make_init(init_func):
            def wrapped(self, *args, **kwargs):
                if isinstance(kwargs.get("text"), str):
                    kwargs["text"] = rtl(kwargs["text"])
                init_func(self, *args, **kwargs)
            return wrapped

        cls.__init__ = make_init(original_init)

        if original_configure is not None:
            def make_config(config_func):
                def wrapped(self, *args, **kwargs):
                    if isinstance(kwargs.get("text"), str):
                        kwargs["text"] = rtl(kwargs["text"])
                    return config_func(self, *args, **kwargs)
                return wrapped

            cls.configure = make_config(original_configure)
            if hasattr(cls, "config"):
                cls.config = cls.configure

    entry_cls = getattr(ctk, "CTkEntry", None)
    if entry_cls is not None:
        original_init = entry_cls.__init__
        original_configure = getattr(entry_cls, "configure", None)

        def entry_init(self, *args, **kwargs):
            if isinstance(kwargs.get("placeholder_text"), str):
                kwargs["placeholder_text"] = rtl(kwargs["placeholder_text"])
            kwargs.setdefault("justify", "right")
            original_init(self, *args, **kwargs)

        entry_cls.__init__ = entry_init

        if original_configure is not None:
            def entry_config(self, *args, **kwargs):
                if isinstance(kwargs.get("placeholder_text"), str):
                    kwargs["placeholder_text"] = rtl(kwargs["placeholder_text"])
                return original_configure(self, *args, **kwargs)

            entry_cls.configure = entry_config
            if hasattr(entry_cls, "config"):
                entry_cls.config = entry_cls.configure

    combo_cls = getattr(ctk, "CTkComboBox", None)
    if combo_cls is not None:
        original_init = combo_cls.__init__
        original_configure = getattr(combo_cls, "configure", None)
        original_get = combo_cls.get
        original_set = combo_cls.set

        def combo_init(self, *args, **kwargs):
            if "values" in kwargs:
                try:
                    kwargs["values"] = [rtl(v) for v in kwargs["values"]]
                except TypeError:
                    pass
            if isinstance(kwargs.get("placeholder_text"), str):
                kwargs["placeholder_text"] = rtl(kwargs["placeholder_text"])
            kwargs.setdefault("justify", "right")
            original_init(self, *args, **kwargs)

        combo_cls.__init__ = combo_init

        if original_configure is not None:
            def combo_config(self, *args, **kwargs):
                if "values" in kwargs:
                    try:
                        kwargs["values"] = [rtl(v) for v in kwargs["values"]]
                    except TypeError:
                        pass
                if isinstance(kwargs.get("placeholder_text"), str):
                    kwargs["placeholder_text"] = rtl(kwargs["placeholder_text"])
                return original_configure(self, *args, **kwargs)

            combo_cls.configure = combo_config
            if hasattr(combo_cls, "config"):
                combo_cls.config = combo_cls.configure

        def combo_get(self):
            return unrtl(original_get(self))

        def combo_set(self, value):
            return original_set(self, rtl(value))

        combo_cls.get = combo_get
        combo_cls.set = combo_set

    ctk._glowva_rtl_text_installed = True


def _patch_view_mapping():
    """Mirror View/Dialog layouts after they are mapped, without patching grid/pack."""
    if getattr(ctk, "_glowva_rtl_mapping_installed", False):
        return

    frame_cls = getattr(ctk, "CTkFrame", None)
    if frame_cls is not None:
        original_frame_init = frame_cls.__init__

        def frame_init(self, *args, **kwargs):
            original_frame_init(self, *args, **kwargs)

            name = self.__class__.__name__
            if name.endswith("View") or name.endswith("Dialog"):
                self.bind(
                    "<Map>",
                    lambda _event, widget=self: widget.after_idle(
                        lambda: mirror_layout(widget)
                    ),
                    add="+",
                )

        frame_cls.__init__ = frame_init

    toplevel_cls = getattr(ctk, "CTkToplevel", None)
    if toplevel_cls is not None:
        original_toplevel_init = toplevel_cls.__init__

        def toplevel_init(self, *args, **kwargs):
            original_toplevel_init(self, *args, **kwargs)

            name = self.__class__.__name__
            if name.endswith("View") or name.endswith("Dialog"):
                self.bind(
                    "<Map>",
                    lambda _event, widget=self: widget.after_idle(
                        lambda: mirror_layout(widget)
                    ),
                    add="+",
                )

        toplevel_cls.__init__ = toplevel_init

    ctk._glowva_rtl_mapping_installed = True


_patch_text_widgets()
_patch_view_mapping()
