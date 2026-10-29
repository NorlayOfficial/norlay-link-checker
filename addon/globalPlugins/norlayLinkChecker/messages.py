# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Short, translatable sentences for failures.

Kept apart from the Gemini client so the client stays NVDA-free and so the
same wording is used by the report and by the settings panel.
"""

from __future__ import annotations

import builtins

_ = builtins._  # noqa: F821


def describe(error) -> str:
	"""Return one sentence for a :class:`GeminiError`."""
	kind = getattr(error, "kind", "")
	detail = getattr(error, "detail", "") or ""

	if kind == "auth":
		return _(
			"Google rejected the API key. Check it in NVDA settings, Norlay "
			"Link Checker.",
		)
	if kind == "quota":
		if detail:
			return _(
				"The free quota is used up. Google asks you to wait about "
				"{seconds} seconds.",
			).format(seconds=int(float(detail)))
		return _("The free daily quota is used up. Try again tomorrow.")
	if kind == "model":
		return _(
			"That model is not available for this key. Choose another model in "
			"NVDA settings, Norlay Link Checker.",
		)
	if kind == "timeout":
		return _("Google did not answer in time. Try again.")
	if kind == "network":
		return _("I could not reach Google. Check that you are online.")
	if kind == "server":
		return _("Google had a problem. Try again in a moment.")
	if kind == "blocked":
		return _("Google refused to explain this address.")
	if kind == "request":
		return _(
			"Google rejected the request. Check the model name in NVDA "
			"settings, Norlay Link Checker.",
		)
	if kind == "config":
		return _(
			"Add your free Gemini API key in NVDA settings, Norlay Link "
			"Checker.",
		)
	return _("Google sent an answer I could not read. Try again.")


def missing_key() -> str:
	return _(
		"Norlay Link Checker needs a free Gemini API key. Open NVDA settings, "
		"Norlay Link Checker, and add one.",
	)


def consent_text(domain: str = "generativelanguage.googleapis.com") -> str:
	return _(
		"This sends the full address to Google Gemini at {domain} so it can be "
		"explained. Nothing else is sent, and nothing is stored. Continue?",
	).format(domain=domain)
