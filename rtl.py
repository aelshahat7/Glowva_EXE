"""Arabic text and explicit RTL layout helpers for Glowva ERP.

This module never monkey-patches Tkinter/CustomTkinter geometry methods.
Text direction is handled with Unicode directional controls, while layout
mirroring is applied explicitly to a completed view with mirror_layout().
"""

RLE = "\u202B"  # Right-to-Left Embedding
PDF = "\u202C"  # Pop Directional Formatting


def rtl(text):
    """Return a display-safe RTL string without changing stored data."""
    if text is None:
        return ""

    text = str(text)

    if not text.strip():
        return ""

    if text.startswith(RLE) and text.endswith(PDF):
        return text

    return f"{RLE}{text}{PDF}"


def unrtl(text):
    """Remove directional controls before storing or comparing values."""
    if text is None:
        return ""

    return str(text).replace(RLE, "").replace(PDF, "")


def _mirror_sticky(sticky):
    if not sticky:
        return sticky

    return str(sticky).translate(
        str.maketrans({"e": "w", "w": "e"})
    )


def _grid_children(parent):
    items = []

    for child in parent.winfo_children():
        try:
            info = child.grid_info()
        except Exception:
            continue

        if not info:
            continue

        try:
            column = int(info.get("column", 0))
            columnspan = max(1, int(info.get("columnspan", 1)))
            row = int(info.get("row", 0))
            rowspan = max(1, int(info.get("rowspan", 1)))
            sticky = info.get("sticky", "")
            items.append(
                (child, column, columnspan, row, rowspan, sticky)
            )
        except (TypeError, ValueError):
            continue

    return items


def _mirror_grid(parent):
    items = _grid_children(parent)

    if not items:
        return

    max_column = max(
        column + columnspan - 1
        for _, column, columnspan, _, _, _ in items
    )

    # Save the existing column configuration before swapping it.
    configs = {}
    for column in range(max_column + 1):
        try:
            cfg = parent.grid_columnconfigure(column)
            configs[column] = {
                "weight": cfg.get("weight", 0),
                "minsize": cfg.get("minsize", 0),
                "pad": cfg.get("pad", 0),
                "uniform": cfg.get("uniform", ""),
            }
        except Exception:
            configs[column] = {}

    # Mirror each child without changing rows or spans.
    for child, column, columnspan, row, rowspan, sticky in items:
        new_column = (
            max_column
            - column
            - columnspan
            + 1
        )

        try:
            child.grid_configure(
                row=row,
                column=new_column,
                rowspan=rowspan,
                columnspan=columnspan,
                sticky=_mirror_sticky(sticky),
            )
        except Exception:
            pass

    # Mirror the column widths/weights too.
    for logical_column, cfg in configs.items():
        actual_column = max_column - logical_column

        try:
            parent.grid_columnconfigure(
                actual_column,
                weight=cfg.get("weight", 0),
                minsize=cfg.get("minsize", 0),
                pad=cfg.get("pad", 0),
                uniform=cfg.get("uniform", ""),
            )
        except Exception:
            pass


def _mirror_pack(parent):
    """Mirror only left/right packed children inside a completed view."""
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
    """Mirror a finished view/dialog recursively without touching app root.

    Call this once after a view has created all of its widgets. It reverses
    grid columns and left/right pack sides while preserving rows, spans,
    weights, and stored data.
    """
    if root is None:
        return

    _mirror_grid(root)
    _mirror_pack(root)

    for child in root.winfo_children():
        mirror_layout(child)
