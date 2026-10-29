# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Read the clipboard without changing it, and say what it holds.

NVDA's :func:`api.getClipData` only understands Unicode text.  When Windows
holds a file or an image instead, asking for text raises an error, which used
to look like a busy clipboard.  A cheap format check first tells the three
cases apart, so the user gets the right explanation.
"""

from __future__ import annotations

import api

#: Clipboard formats from Windows.h.  Only the two that matter here.
CF_UNICODETEXT = 13
CF_HDROP = 15


class ClipboardProblem(Exception):
	"""The clipboard could not be read, or holds something that is not text."""


class ClipboardUnavailable(ClipboardProblem):
	"""The clipboard could not be read, usually because another app has it."""


class ClipboardHasFiles(ClipboardProblem):
	"""The clipboard holds one or more files, not text."""


class ClipboardHasNoText(ClipboardProblem):
	"""The clipboard holds a format that is neither text nor files."""


def _clipboard_kind() -> str | None:
	"""Return ``text``, ``files``, ``other``, ``empty`` or ``locked``.

	``None`` means the formats could not be inspected, so the caller should
	fall back to asking NVDA for text.  This is also what happens on platforms
	other than Windows, where the tests run.

	The clipboard is opened briefly to list its formats.  That also proves
	whether another app is holding it, which is different from it being empty.
	"""
	try:
		import ctypes

		user32 = ctypes.windll.user32
		if not user32.OpenClipboard(None):
			return "locked"
		try:
			formats = set()
			format_id = 0
			while True:
				format_id = user32.EnumClipboardFormats(format_id)
				if not format_id:
					break
				formats.add(format_id)
		finally:
			user32.CloseClipboard()
	except Exception:
		return None
	if not formats:
		return "empty"
	if CF_HDROP in formats:
		return "files"
	if CF_UNICODETEXT in formats:
		return "text"
	return "other"


def read_clipboard_text() -> str:
	"""Return the clipboard's text, or raise a :class:`ClipboardProblem`.

	The clipboard is only read when the user runs a command.  It is never
	written, cleared or restored by this add-on.
	"""
	kind = _clipboard_kind()
	if kind == "locked":
		raise ClipboardUnavailable("locked")
	if kind == "files":
		raise ClipboardHasFiles()
	if kind == "other":
		raise ClipboardHasNoText()
	if kind == "empty":
		return ""
	try:
		text = api.getClipData()
	except Exception as error:
		# Do not keep the exception text: it is not useful to the user and it
		# could in principle contain clipboard content on some platforms.
		raise ClipboardUnavailable(type(error).__name__) from error
	return text or ""
