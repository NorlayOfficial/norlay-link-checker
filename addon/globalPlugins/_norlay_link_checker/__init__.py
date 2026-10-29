# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Pure-Python core of the Norlay Link Checker.

This package deliberately imports nothing from NVDA.  It only looks at the
text it is given, never opens a link, never uses the network and never writes
anything to disk.  That keeps it unit testable and easy to audit.
"""

from __future__ import annotations

from .analyzer import analyze
from .model import Analysis, Finding, HostInfo, ParsedURL
from .parse import (
	MAX_URL_CHARS,
	InvalidURL,
	LinkCheckerError,
	NoURLFound,
	URLTooLong,
	extract_urls,
	parse_url,
)
from .report import render_report, short_summary

__all__ = [
	"Analysis",
	"Finding",
	"HostInfo",
	"InvalidURL",
	"LinkCheckerError",
	"MAX_URL_CHARS",
	"NoURLFound",
	"ParsedURL",
	"URLTooLong",
	"analyze",
	"extract_urls",
	"parse_url",
	"render_report",
	"short_summary",
]
