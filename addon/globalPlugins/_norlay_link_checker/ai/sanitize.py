# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Turn a model reply into clean plain text for a read-only field.

Models answer in Markdown by default.  Asterisks and backticks are noise in a
text control and in speech, so they are removed rather than displayed.
"""

from __future__ import annotations

import re

#: Longest explanation shown.  Anything beyond this is cut at a word boundary.
MAX_REPORT_CHARS = 1500

_FENCE = re.compile(r"^\s*```.*$", re.MULTILINE)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_BOLD = re.compile(r"(\*\*|__)(.+?)\1")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BULLET = re.compile(r"^\s{0,2}[-*+]\s+", re.MULTILINE)
_NUMBERED = re.compile(r"^\s{0,2}\d+[.)]\s+", re.MULTILINE)
_SPACES = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def clean(text: str) -> str:
	"""Return *text* as plain, wrapped-ready prose."""
	if not text:
		return ""
	result = text.replace("\r\n", "\n").replace("\r", "\n")
	result = _FENCE.sub("", result)
	result = _INLINE_CODE.sub(r"\1", result)
	result = _BOLD.sub(r"\2", result)
	result = _HEADING.sub("", result)
	result = _BULLET.sub("", result)
	result = _NUMBERED.sub("", result)
	result = _SPACES.sub(" ", result)
	result = _BLANK_LINES.sub("\n\n", result)
	result = result.strip()
	if len(result) > MAX_REPORT_CHARS:
		cut = result.rfind(" ", 0, MAX_REPORT_CHARS)
		result = result[: cut if cut > 0 else MAX_REPORT_CHARS].rstrip() + "…"
	return result
