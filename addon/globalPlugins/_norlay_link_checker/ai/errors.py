# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Failures that are safe to describe to the user.

The exception carries a short ``kind`` instead of a message, so the NVDA
adapter can translate it and so the request, the address and the key can
never leak into the log through an exception string.
"""

from __future__ import annotations


class GeminiError(Exception):
	"""One failed request to Gemini.

	``kind`` is one of ``config``, ``auth``, ``quota``, ``model``,
	``timeout``, ``network``, ``server``, ``blocked`` or ``response``.
	``detail`` is optional extra information, such as the number of seconds
	Google asks us to wait.
	"""

	def __init__(self, kind: str, detail: str = "") -> None:
		super().__init__(kind)
		self.kind = kind
		self.detail = detail

	def __str__(self) -> str:
		return f"GeminiError({self.kind})"
