"""Arabic text shaping and right-to-left display helpers for Glowva ERP.

This module handles TEXT direction only. It does not modify grid(), pack(),
or any Tk/CustomTkinter geometry behavior.
"""

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # pragma: no cover
    arabic_reshaper = None
    get_display = None

RLE = "\u202B"
PDF = "\u202C"

_ARABIC_RANGES = (
    ("\u0600", "\u06FF"),
    ("\u0750", "\u077F"),
    ("\u08A0", "\u08FF"),
    ("\uFB50", "\uFDFF"),
    ("\uFE70", "\uFEFF"),
)

# Values displayed through rtl() may later come back through unrtl(),
# especially ComboBox selections. Keep the original logical value so
# nothing visually-shaped is written into the database.
_DISPLAY_TO_LOGICAL = {}


def _contains_arabic(text):
    return any(
        start <= char <= end
        for char in str(text)
        for start, end in _ARABIC_RANGES
    )


def rtl(text):
    """Return text rendered in correct Arabic visual order."""
    if text is None:
        return ""

    logical = str(text)

    if not logical.strip() or not _contains_arabic(logical):
        return logical

    if arabic_reshaper is None or get_display is None:
        return f"{RLE}{logical}{PDF}"

    try:
        reshaped = arabic_reshaper.reshape(logical)
        visual = get_display(reshaped)
    except Exception:
        return f"{RLE}{logical}{PDF}"

    _DISPLAY_TO_LOGICAL[visual] = logical
    return visual


def unrtl(text):
    """Return the original logical string for text produced by rtl()."""
    if text is None:
        return ""

    value = str(text)

    if value in _DISPLAY_TO_LOGICAL:
        return _DISPLAY_TO_LOGICAL[value]

    return value.replace(RLE, "").replace(PDF, "")
