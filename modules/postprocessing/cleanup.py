"""
Small, conservative fixes for artifacts that marker-pdf commonly produces.

All functions are pure (str -> str) and idempotent.
"""
from __future__ import annotations

import re

# "<sup>&</sup>lt;sup>7</sup>": an escaped "<sup>" that was itself wrapped
# in a superscript. Restore the intended "<sup>7</sup>".
_ESCAPED_SUP_RE = re.compile(r"<sup>&</sup>lt;sup>")

# " <sup>Y</sup> ": a single small-caps letter (typically the conjunction
# "Y"/"y" in uppercase headings) misdetected as a superscript. Only fixed
# when surrounded by whitespace, so real superscripts such as ordinals
# ("1<sup>a</sup>") or exponents ("x<sup>n</sup>") are left untouched.
_SPACED_LETTER_SUP_RE = re.compile(r"(?<=\s)<sup>([^\W\d_])</sup>(?=\s)")

# "identifi cado", "fi rmas", "confl ictos": the PDF's fi/fl ligature glyph was
# extracted followed by a spurious space. No common Spanish or English word
# ends in "fi"/"fl", so joining a token that ends in these letters with a
# following lowercase word is safe. ("ff" is deliberately excluded: "off",
# "staff", ...)
_LIGATURE_SPLIT_RE = re.compile(r"(?<![^\W\d_])([^\W\d_]*?(?:fi|fl)) (?=[a-záéíóúñüàèìòùçâêîôûäëïö])")


def fix_escaped_sup(text: str) -> str:
    return _ESCAPED_SUP_RE.sub("<sup>", text)


def fix_spaced_letter_sup(text: str) -> str:
    return _SPACED_LETTER_SUP_RE.sub(r"\1", text)


def fix_ligature_splits(text: str) -> str:
    return _LIGATURE_SPLIT_RE.sub(r"\1", text)


def clean_markdown(text: str, ligatures: bool = True) -> str:
    """Apply all cleanup fixes."""
    text = fix_escaped_sup(text)
    text = fix_spaced_letter_sup(text)
    if ligatures:
        text = fix_ligature_splits(text)
    return text
