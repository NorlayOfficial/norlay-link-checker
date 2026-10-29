# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Turn clipboard text into an analysis the report can render."""

from __future__ import annotations

from .checks import run_checks
from .model import Analysis
from .parse import (
	MAX_URL_CHARS,
	InvalidURL,
	NoURLFound,
	URLTooLong,
	build_host_info,
	extract_urls,
	parse_url,
)


def analyze(text: str) -> Analysis:
	"""Analyse the first link in *text*.

	Raises :class:`NoURLFound` when there is no link, :class:`InvalidURL` when
	the link cannot be read, and :class:`URLTooLong` for a single oversized
	link.  The result never leaves the machine.
	"""
	if not text or not text.strip():
		raise NoURLFound("empty")

	truncated = len(text) > MAX_URL_CHARS
	urls = extract_urls(text[:MAX_URL_CHARS])
	if not urls:
		raise NoURLFound("no_url")

	parsed = parse_url(urls[0])
	host_info = build_host_info(parsed)
	findings = run_checks(parsed, host_info)
	return Analysis(
		parsed=parsed,
		host_info=host_info,
		findings=findings,
		url_count=len(urls),
		truncated=truncated,
	)


__all__ = [
	"Analysis",
	"InvalidURL",
	"MAX_URL_CHARS",
	"NoURLFound",
	"URLTooLong",
	"analyze",
]
