"""Arabic text direction helpers for Glowva ERP.

Tkinter/CustomTkinter does not provide a reliable application-wide RTL
layout mode. This module therefore handles TEXT direction only.

We use an explicit RTL embedding mark (RLE/PDF) instead of reordering
characters. This keeps the stored Arabic string unchanged while telling
the text renderer to treat the phrase as a right-to-left run.
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

    # Avoid nesting our directional marks when a value is already wrapped.
    if text.startswith(RLE) and text.endswith(PDF):
        return text

    return f"{RLE}{text}{PDF}"


def unrtl(text):
    """Remove directional control characters before storing/comparing data."""
    if text is None:
        return ""

    return str(text).replace(RLE, "").replace(PDF, "")
