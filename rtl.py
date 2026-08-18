"""
Force correct right-to-left word order for Arabic text in Tkinter/
CustomTkinter widgets, on Windows systems whose system locale is NOT
Arabic (e.g. "English (United States)").

Why this is needed: Tk's text layout engine picks a paragraph direction
based on system locale when it isn't told otherwise. On a non-Arabic
locale, it can default to left-to-right paragraph flow even for Arabic
text - so a phrase like "لوحة التحكم" (word1 word2) gets its WORDS laid
out in the wrong order on screen, even though each word's letters join
and shape correctly on their own (Windows' font shaping - Uniscribe/
DirectWrite - already handles Arabic letter joining automatically;
that part was never broken).

The fix: prepend the invisible Unicode "Right-to-Left Mark" (RLM,
U+200F). RLM adds zero visible characters and touches none of the
existing text - it's purely a directional hint that tells the layout
engine "treat this run as right-to-left," so multi-word Arabic lays
out start-to-end in the correct visual order.

This deliberately does NOT reorder characters or words in the string
(that was the previous, incorrect approach using arabic_reshaper +
bidi.get_display - confirmed to cause its own separate letter-order
corruption on top of the layout issue this module fixes).
"""

RLM = "\u200F"  # Right-to-Left Mark - invisible, zero-width


def rtl(text):
    if text is None:
        return ""

    text = str(text)

    if not text.strip():
        return ""

    return RLM + text


def unrtl(text):
    """
    Inverse of rtl(): strips the RLM mark rtl() adds, so a value read
    back from a widget (e.g. combobox.get()) can be safely stored in the
    database or compared against raw values, instead of accidentally
    carrying an invisible directional character into storage/comparison.
    """
    if text is None:
        return ""

    return str(text).replace(RLM, "")