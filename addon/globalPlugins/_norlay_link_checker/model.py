# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Data types shared by the parser, the checks and the report."""

from __future__ import annotations

from dataclasses import dataclass

#: A pattern that is worth a warning.
WARNING = "warning"
#: Useful context, but not a warning on its own.
NOTE = "note"


@dataclass(frozen=True)
class Finding:
	"""One observation about a link.

	``code`` is a short stable identifier used by tests and by the log.  It is
	never shown to the user.  ``message`` is the full plain-language sentence
	shown in the report, including why the pattern can matter.
	"""

	code: str
	severity: str
	message: str


@dataclass(frozen=True)
class ParsedURL:
	"""The structural parts of one link, as written.

	``kind`` is one of ``web``, ``email``, ``phone``, ``script``, ``data``,
	``local`` or ``other``.  Only ``web`` links have a meaningful host.
	"""

	raw: str
	scheme: str | None
	kind: str
	host: str
	host_ascii: str
	host_input: str
	port: int | None
	port_text: str | None
	port_error: str | None
	userinfo: str | None
	path: str
	query: str | None
	fragment: str | None
	trailing_dot: bool
	percent_encoded_host: bool
	is_ip: bool
	ip_version: int | None

	@property
	def has_host(self) -> bool:
		return bool(self.host)


@dataclass(frozen=True)
class HostInfo:
	"""The domain breakdown, computed from the bundled Public Suffix List."""

	public_suffix: str
	registrable: str
	subdomain: str
	psl_available: bool = True


@dataclass
class Analysis:
	"""Everything the report needs about one clipboard check."""

	parsed: ParsedURL
	host_info: HostInfo | None
	findings: list[Finding]
	url_count: int = 1
	truncated: bool = False

	@property
	def warning_count(self) -> int:
		return sum(1 for finding in self.findings if finding.severity == WARNING)

	@property
	def note_count(self) -> int:
		return sum(1 for finding in self.findings if finding.severity == NOTE)
