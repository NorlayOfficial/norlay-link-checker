# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The instructions sent to Gemini.

The prompt is deliberately short: fewer input tokens means less quota used,
and a narrower job means fewer confident mistakes.
"""

from __future__ import annotations

import urllib.parse

#: Largest address sent to the model.  Longer links are cut with a marker.
MAX_PROMPT_URL_CHARS = 2048

SYSTEM_PROMPT = (
	"You explain web addresses to a screen reader user. You only see the "
	"address text. You have not opened the page and cannot know what it "
	"contains.\n\n"
	"Reply in plain text, at most 80 words, with no markdown, no lists and no "
	"headings. Say what the address appears to be: the site or organisation "
	"it points to, the likely purpose suggested by its path and query, and "
	"anything that deserves caution, such as a lookalike name or an unusual "
	"subdomain.\n\n"
	"Never say that a link is safe or unsafe. Never claim to know what the "
	"page shows. Say plainly when something is uncertain."
)


def shorten_url(url: str, limit: int = MAX_PROMPT_URL_CHARS) -> str:
	"""Cut an oversized address so one paste cannot spend the whole quota."""
	if len(url) <= limit:
		return url
	return url[:limit] + " [truncated]"


def build_user_text(url: str, facts: list[str] | tuple[str, ...] = ()) -> str:
	"""Compose the single user message: the address plus short local facts."""
	lines = [f"Address: {shorten_url(url)}"]
	useful = [fact.strip() for fact in facts if fact and fact.strip()]
	if useful:
		lines.append("Facts already known: " + "; ".join(useful))
	return "\n".join(lines)


def without_query(url: str) -> str:
	"""Drop the query and fragment, which often carry tokens and identifiers."""
	parts = urllib.parse.urlsplit(url)
	if not parts.query and not parts.fragment:
		return url
	return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
