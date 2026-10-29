# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.
#
# The Public Suffix List data in data/public_suffix_list.dat is
# Copyright Mozilla Foundation and contributors, licensed under the
# Mozilla Public License 2.0.  See LICENSE-PSL.txt.

"""Registrable domain lookup using a bundled Public Suffix List snapshot.

The list is read from disk once, on first use, and kept in memory for the
lifetime of the process.  No network access is ever performed.
"""

from __future__ import annotations

import os

DATA_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PSL_FILENAME = "public_suffix_list.dat"


class DomainDataError(Exception):
	"""Raised when the bundled Public Suffix List cannot be read."""


_rules: frozenset[str] | None = None


def _load_rules() -> frozenset[str]:
	global _rules
	if _rules is not None:
		return _rules
	path = os.path.join(DATA_DIRECTORY, PSL_FILENAME)
	rules: set[str] = set()
	try:
		with open(path, encoding="utf-8") as handle:
			for line in handle:
				line = line.strip()
				if not line or line.startswith("//"):
					continue
				rules.add(line.lower())
	except OSError as error:
		raise DomainDataError(str(error)) from error
	if not rules:
		raise DomainDataError("the Public Suffix List file is empty")
	_rules = frozenset(rules)
	return _rules


def _public_suffix_label_count(labels: list[str]) -> int:
	"""Return how many trailing labels form the public suffix."""
	rules = _load_rules()
	count = len(labels)
	best = 1  # The implicit "*" rule.
	exception: int | None = None
	for start in range(count):
		suffix = ".".join(labels[start:])
		suffix_length = count - start
		if suffix in rules:
			best = max(best, suffix_length)
		if start > 0 and f"*.{suffix}" in rules:
			best = max(best, suffix_length + 1)
		if f"!{suffix}" in rules and (
			exception is None or suffix_length > exception
		):
			exception = suffix_length
	if exception is not None:
		# An exception rule removes its leftmost label from the suffix.
		return max(1, exception - 1)
	return min(best, count)


def has_known_suffix(host: str) -> bool:
	"""Whether *host* ends in a suffix from the bundled Public Suffix List.

	:func:`public_suffix` falls back to the implicit ``*`` rule, so any last
	label counts, which makes ``report.pdf`` look like a domain.  Bare text is
	checked with this instead, so file names and dotted words are not mistaken
	for links.  It returns False for a host with fewer than two labels.
	"""
	labels = host.lower().rstrip(".").split(".")
	if len(labels) < 2:
		return False
	rules = _load_rules()
	for start in range(1, len(labels)):
		suffix = ".".join(labels[start:])
		if suffix in rules or f"*.{suffix}" in rules:
			return True
	return False


def public_suffix(host: str) -> str:
	"""Return the public suffix of *host* (for example ``co.uk``)."""
	labels = host.lower().split(".")
	return ".".join(labels[-_public_suffix_label_count(labels) :])


def registrable_domain(host: str) -> str:
	"""Return the domain that a site owner actually controls.

	``login.example.co.uk`` gives ``example.co.uk``; ``user.github.io`` gives
	``user.github.io`` because ``github.io`` is itself a public suffix.
	"""
	host = host.lower().rstrip(".")
	if not host:
		return ""
	labels = host.split(".")
	if len(labels) < 2:
		return host
	suffix_length = _public_suffix_label_count(labels)
	if suffix_length >= len(labels):
		return host
	return ".".join(labels[-(suffix_length + 1) :])
