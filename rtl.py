import arabic_reshaper
from bidi.algorithm import get_display


def rtl(text):
    if text is None:
        return ""

    text = str(text)

    if not text.strip():
        return ""

    return get_display(
        arabic_reshaper.reshape(text)
    )