import re
from datetime import datetime, date, timedelta


# ==========================================================
# Unicode Direction Controls
# ==========================================================

RLE = "\u202B"
LRE = "\u202A"
PDF = "\u202C"


# ==========================================================
# Detect Arabic
# ==========================================================

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


# ==========================================================
# Date Display
# ==========================================================

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

    # Excel / Google Sheets serial dates, including strings like 46231.0
    try:
        serial = float(text.replace(",", ""))
        if 20000 <= serial <= 80000:
            base = datetime(1899, 12, 30)
            return (base + timedelta(days=serial)).strftime("%d/%m/%Y")
    except (TypeError, ValueError, OverflowError):
        pass

    # Common date formats
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


# ==========================================================
# RTL Display
# ==========================================================

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

    return str(text).replace(
        "\u200E", ""
    ).replace(
        "\u200F", ""
    ).replace(
        "\u202A", ""
    ).replace(
        "\u202B", ""
    ).replace(
        "\u202C", ""
    ).replace(
        "\u202D", ""
    ).replace(
        "\u202E", ""
    )
