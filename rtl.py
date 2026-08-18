import re


# ==========================================================
# Unicode Direction Controls
# ==========================================================

RLE = "\u202B"   # Right-to-Left Embedding
LRE = "\u202A"   # Left-to-Right Embedding
PDF = "\u202C"   # Pop Directional Formatting


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

    # لو عربي فقط: نعكس ترتيب الكلمات
    if not re.search(r"[A-Za-z0-9]", text):
        return " ".join(reversed(text.split()))

    # النص المختلط:
    # نعكس ترتيب الكلمات، لكن نحافظ على كل Token كما هو
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