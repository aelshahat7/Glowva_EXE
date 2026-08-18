"""Central RTL support for Glowva ERP's Tkinter/CustomTkinter UI.

Arabic in Tk on an English Windows locale often needs an explicit RTL
paragraph direction. We use an invisible Right-to-Left Mark (U+200F)
for display text, and we apply that consistently to the common
CustomTkinter widgets so views do not need to wrap every label manually.

The layout helper mirrors grid columns inside views while intentionally
leaving the main application's root layout alone. This lets the existing
sidebar remain on the right and makes each screen's internal layout RTL.
"""

import tkinter as tk
import customtkinter as ctk

RLM = "\u200F"

# Arabic presentation / script ranges. We only add RTL metadata when the
# string actually contains Arabic, so numeric-only and English strings are
# left untouched.
_ARABIC_RANGES = (
    ("\u0600", "\u06FF"),
    ("\u0750", "\u077F"),
    ("\u08A0", "\u08FF"),
    ("\uFB50", "\uFDFF"),
    ("\uFE70", "\uFEFF"),
)


def _contains_arabic(text):
    for char in text:
        for start, end in _ARABIC_RANGES:
            if start <= char <= end:
                return True
    return False


def rtl(text):
    """Return text with an invisible RTL paragraph hint."""
    if text is None:
        return ""

    text = str(text)

    if not text.strip() or not _contains_arabic(text):
        return text

    if text.startswith(RLM):
        return text

    return RLM + text


def unrtl(text):
    """Remove the invisible RTL marks before storing/comparing values."""
    if text is None:
        return ""

    return str(text).replace(RLM, "")


def _wrap_text_option(kwargs, key="text"):
    if key in kwargs and isinstance(kwargs[key], str):
        kwargs[key] = rtl(kwargs[key])


def _wrap_values(values):
    if values is None:
        return values

    try:
        return [rtl(value) for value in values]
    except TypeError:
        return values


def _mirror_sticky(sticky):
    if not sticky:
        return sticky

    chars = str(sticky)
    return chars.translate(str.maketrans({"e": "w", "w": "e"}))


def _should_mirror_parent(parent):
    """Mirror layouts inside application views, not the root app columns."""
    try:
        return parent.__class__.__name__ != "GlowvaApp"
    except Exception:
        return True


def _remember_grid_config(parent, column):
    cache = getattr(parent, "_rtl_grid_configs", None)
    if cache is None:
        cache = {}
        setattr(parent, "_rtl_grid_configs", cache)

    if column not in cache:
        try:
            cfg = parent.grid_columnconfigure(column)
            cache[column] = {
                "weight": cfg.get("weight", 0),
                "minsize": cfg.get("minsize", 0),
                "pad": cfg.get("pad", 0),
                "uniform": cfg.get("uniform", ""),
            }
        except Exception:
            cache[column] = {
                "weight": 0,
                "minsize": 0,
                "pad": 0,
                "uniform": "",
            }


def _reflow_grid(parent):
    if not _should_mirror_parent(parent):
        return

    children = []

    try:
        for child in parent.winfo_children():
            logical = getattr(child, "_rtl_logical_grid", None)
            if not logical:
                continue

            col, span, sticky = logical
            children.append((child, col, span, sticky))
    except Exception:
        return

    if not children:
        return

    max_column = max(
        col + max(span, 1) - 1
        for _, col, span, _ in children
    )

    for child, col, span, sticky in children:
        new_col = max_column - col - max(span, 1) + 1
        new_sticky = _mirror_sticky(sticky)

        try:
            tk.Grid.grid_configure(
                child,
                column=new_col,
                columnspan=span,
                sticky=new_sticky,
            )
        except Exception:
            pass

    # Mirror column sizing as well, so a wide input column stays wide after
    # the labels/inputs swap sides.
    try:
        for logical_col in range(max_column + 1):
            _remember_grid_config(parent, logical_col)

        cache = getattr(parent, "_rtl_grid_configs", {})
        for logical_col, cfg in cache.items():
            if logical_col > max_column:
                continue

            actual_col = max_column - logical_col
            parent.grid_columnconfigure(
                actual_col,
                weight=cfg["weight"],
                minsize=cfg["minsize"],
                pad=cfg["pad"],
                uniform=cfg["uniform"],
            )
    except Exception:
        pass


def apply_rtl_layout(root):
    """Mirror grid/pack children recursively inside a screen/dialog."""
    if root is None:
        return

    try:
        _reflow_grid(root)
    except Exception:
        pass

    try:
        for child in root.winfo_children():
            apply_rtl_layout(child)
    except Exception:
        pass


def _patch_widget_classes():
    """Patch common CustomTkinter widgets once, before views are created."""
    if getattr(ctk, "_glowva_rtl_installed", False):
        return

    # ----------------------------------------------------------
    # Labels / Buttons / other text-bearing widgets
    # ----------------------------------------------------------
    text_widgets = [
        "CTkLabel",
        "CTkButton",
        "CTkCheckBox",
        "CTkRadioButton",
        "CTkSwitch",
        "CTkOptionMenu",
    ]

    for class_name in text_widgets:
        cls = getattr(ctk, class_name, None)
        if cls is None:
            continue

        original_init = cls.__init__
        original_configure = getattr(cls, "configure", None)

        def make_init(init_func):
            def rtl_init(self, *args, **kwargs):
                _wrap_text_option(kwargs)
                init_func(self, *args, **kwargs)
            return rtl_init

        cls.__init__ = make_init(original_init)

        if original_configure is not None:
            def make_config(config_func):
                def rtl_config(self, *args, **kwargs):
                    _wrap_text_option(kwargs)
                    return config_func(self, *args, **kwargs)
                return rtl_config

            cls.configure = make_config(original_configure)

            if hasattr(cls, "config"):
                cls.config = cls.configure

    # ----------------------------------------------------------
    # Entry: right-aligned Arabic input + RTL placeholder
    # ----------------------------------------------------------
    entry_cls = getattr(ctk, "CTkEntry", None)
    if entry_cls is not None:
        original_entry_init = entry_cls.__init__
        original_entry_configure = getattr(entry_cls, "configure", None)

        def entry_init(self, *args, **kwargs):
            if isinstance(kwargs.get("placeholder_text"), str):
                kwargs["placeholder_text"] = rtl(kwargs["placeholder_text"])
            kwargs.setdefault("justify", "right")
            original_entry_init(self, *args, **kwargs)

        entry_cls.__init__ = entry_init

        if original_entry_configure is not None:
            def entry_config(self, *args, **kwargs):
                if isinstance(kwargs.get("placeholder_text"), str):
                    kwargs["placeholder_text"] = rtl(kwargs["placeholder_text"])
                return original_entry_configure(self, *args, **kwargs)

            entry_cls.configure = entry_config
            if hasattr(entry_cls, "config"):
                entry_cls.config = entry_cls.configure

    # ----------------------------------------------------------
    # ComboBox: display values RTL, but get() returns clean data
    # ----------------------------------------------------------
    combo_cls = getattr(ctk, "CTkComboBox", None)
    if combo_cls is not None:
        original_combo_init = combo_cls.__init__
        original_combo_configure = getattr(combo_cls, "configure", None)
        original_combo_get = combo_cls.get
        original_combo_set = combo_cls.set

        def combo_init(self, *args, **kwargs):
            if "values" in kwargs:
                kwargs["values"] = _wrap_values(kwargs["values"])
            if isinstance(kwargs.get("placeholder_text"), str):
                kwargs["placeholder_text"] = rtl(kwargs["placeholder_text"])
            kwargs.setdefault("justify", "right")
            original_combo_init(self, *args, **kwargs)

        combo_cls.__init__ = combo_init

        if original_combo_configure is not None:
            def combo_config(self, *args, **kwargs):
                if "values" in kwargs:
                    kwargs["values"] = _wrap_values(kwargs["values"])
                if isinstance(kwargs.get("placeholder_text"), str):
                    kwargs["placeholder_text"] = rtl(kwargs["placeholder_text"])
                return original_combo_configure(self, *args, **kwargs)

            combo_cls.configure = combo_config
            if hasattr(combo_cls, "config"):
                combo_cls.config = combo_cls.configure

        def combo_get(self):
            return unrtl(original_combo_get(self))

        def combo_set(self, value):
            return original_combo_set(self, rtl(value))

        combo_cls.get = combo_get
        combo_cls.set = combo_set

    # ----------------------------------------------------------
    # Textbox: RTL text direction for static content / cursor text
    # ----------------------------------------------------------
    textbox_cls = getattr(ctk, "CTkTextbox", None)
    if textbox_cls is not None:
        original_textbox_init = textbox_cls.__init__

        def textbox_init(self, *args, **kwargs):
            kwargs.setdefault("activate_scrollbars", True)
            original_textbox_init(self, *args, **kwargs)

        textbox_cls.__init__ = textbox_init

    # ----------------------------------------------------------
    # Grid: mirror internal layouts inside views, not GlowvaApp root
    # ----------------------------------------------------------
    base_cls = getattr(ctk, "CTkBaseClass", None)
    if base_cls is not None and not getattr(base_cls, "_glowva_rtl_grid", False):
        def rtl_grid(self, *args, **kwargs):
            parent = getattr(self, "master", None)

            has_layout_args = any(
                key in kwargs
                for key in ("column", "columnspan", "row", "rowspan", "sticky")
            )

            if parent is not None and _should_mirror_parent(parent):
                if has_layout_args or not hasattr(self, "_rtl_logical_grid"):
                    col = int(kwargs.get("column", 0) or 0)
                    span = int(kwargs.get("columnspan", 1) or 1)
                    sticky = kwargs.get("sticky", "") or ""
                    self._rtl_logical_grid = (col, span, sticky)

                result = tk.Grid.grid(self, *args, **kwargs)

                try:
                    parent.after_idle(lambda p=parent: _reflow_grid(p))
                except Exception:
                    pass

                return result

            return tk.Grid.grid(self, *args, **kwargs)

        base_cls.grid = rtl_grid
        base_cls.grid_configure = tk.Grid.grid_configure
        base_cls._glowva_rtl_grid = True

    # ----------------------------------------------------------
    # Pack: reverse left/right packing inside views
    # ----------------------------------------------------------
    if base_cls is not None and not getattr(base_cls, "_glowva_rtl_pack", False):
        def rtl_pack(self, *args, **kwargs):
            parent = getattr(self, "master", None)
            if parent is not None and _should_mirror_parent(parent):
                side = kwargs.get("side")
                if side == "left":
                    kwargs["side"] = "right"
                elif side == "right":
                    kwargs["side"] = "left"

            return tk.Pack.pack(self, *args, **kwargs)

        base_cls.pack = rtl_pack
        base_cls.pack_configure = tk.Pack.pack_configure
        base_cls._glowva_rtl_pack = True

    ctk._glowva_rtl_installed = True


# Installation is automatic because main.py already imports rtl before
# importing the views. No per-view boilerplate is required.
_patch_widget_classes()
