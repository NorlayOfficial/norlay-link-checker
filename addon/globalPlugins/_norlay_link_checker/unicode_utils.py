# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Small Unicode helpers used by the checks.

Everything here is a lookup table plus ``unicodedata``.  No locale, network or
platform state is involved, so results are identical on every machine.
"""

from __future__ import annotations

import unicodedata

LATIN = "Latin"
CYRILLIC = "Cyrillic"
GREEK = "Greek"
HAN = "Han"
HIRAGANA = "Hiragana"
KATAKANA = "Katakana"
HANGUL = "Hangul"
ARABIC = "Arabic"
HEBREW = "Hebrew"
THAI = "Thai"
DEVANAGARI = "Devanagari"

# Half-open code point ranges.  Only scripts that matter for lookalike
# detection are listed; anything else is reported as None.
_SCRIPT_RANGES: tuple[tuple[int, int, str], ...] = (
	(0x0041, 0x005B, LATIN),
	(0x0061, 0x007B, LATIN),
	(0x00AA, 0x00AB, LATIN),
	(0x00BA, 0x00BB, LATIN),
	(0x00C0, 0x0250, LATIN),
	(0x0250, 0x02B9, LATIN),
	(0x1D00, 0x1D26, LATIN),
	(0x1E00, 0x1F00, LATIN),
	(0x2C60, 0x2C80, LATIN),
	(0xA720, 0xA800, LATIN),
	(0xAB30, 0xAB70, LATIN),
	(0xFF21, 0xFF3B, LATIN),
	(0xFF41, 0xFF5B, LATIN),
	(0x0370, 0x0400, GREEK),
	(0x1F00, 0x2000, GREEK),
	(0x0400, 0x0530, CYRILLIC),
	(0x1C80, 0x1C90, CYRILLIC),
	(0x2DE0, 0x2E00, CYRILLIC),
	(0xA640, 0xA6A0, CYRILLIC),
	(0x0590, 0x0600, HEBREW),
	(0x0600, 0x0700, ARABIC),
	(0x0750, 0x0780, ARABIC),
	(0x08A0, 0x0900, ARABIC),
	(0xFB50, 0xFE00, ARABIC),
	(0xFE70, 0xFF00, ARABIC),
	(0x0900, 0x0980, DEVANAGARI),
	(0x0E00, 0x0E80, THAI),
	(0x3040, 0x30A0, HIRAGANA),
	(0x30A0, 0x3100, KATAKANA),
	(0x31F0, 0x3200, KATAKANA),
	(0x1100, 0x1200, HANGUL),
	(0x3130, 0x3190, HANGUL),
	(0xAC00, 0xD7B0, HANGUL),
	(0x3400, 0x4DC0, HAN),
	(0x4E00, 0xA000, HAN),
	(0xF900, 0xFB00, HAN),
)

#: Scripts whose letters are commonly used to imitate Latin letters.
CONFUSABLE_WITH_LATIN = frozenset({CYRILLIC, GREEK})

_BIDI_CONTROLS = frozenset(
	"\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e"
	"\u2066\u2067\u2068\u2069",
)

_ZERO_WIDTH = frozenset("\u200b\u200c\u200d\u2060\ufeff")


def script_of(character: str) -> str | None:
	"""Return a coarse script name for one character, or ``None``."""
	point = ord(character)
	for start, end, name in _SCRIPT_RANGES:
		if start <= point < end:
			return name
	return None


def scripts_in(text: str) -> set[str]:
	"""Return the set of strong scripts used in *text*."""
	return {script for character in text if (script := script_of(character))}


def has_confusable_mix(text: str) -> bool:
	"""True when *text* mixes Latin with Cyrillic or Greek letters."""
	scripts = scripts_in(text)
	return LATIN in scripts and bool(scripts & CONFUSABLE_WITH_LATIN)


def is_bidi_control(character: str) -> bool:
	return character in _BIDI_CONTROLS


def is_zero_width(character: str) -> bool:
	return character in _ZERO_WIDTH


def is_control(character: str) -> bool:
	point = ord(character)
	return point < 0x20 or 0x7F <= point <= 0x9F


def count_characters(text: str, predicate) -> int:
	return sum(1 for character in text if predicate(character))


def compatible_form(text: str) -> str:
	"""Return the NFKC normal form of *text*."""
	return unicodedata.normalize("NFKC", text)


#: Characters escaped in the report so that invisible input becomes visible.
_ESCAPED = _BIDI_CONTROLS | _ZERO_WIDTH


def escape_for_display(text: str, limit: int = 300) -> str:
	"""Make invisible or control characters visible, then shorten.

	The result is plain text and is never interpreted as markup.
	"""
	pieces: list[str] = []
	truncated = False
	for index, character in enumerate(text):
		if index >= limit:
			truncated = True
			break
		if is_control(character) or character in _ESCAPED:
			pieces.append(f"<U+{ord(character):04X}>")
		else:
			pieces.append(character)
	result = "".join(pieces)
	if truncated:
		result += "..."
	return result


def describe_character(character: str) -> str:
	"""Return ``U+XXXX`` for a character, for use in a warning."""
	return f"U+{ord(character):04X}"
