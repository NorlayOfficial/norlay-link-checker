#!/usr/bin/env python3
# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Print the changelog section for one version, for a GitHub release body."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "changelog.md"


def section(version: str) -> str:
	text = CHANGELOG.read_text(encoding="utf-8")
	heading = re.compile(
		rf"^# Norlay Link Checker {re.escape(version)}\s*$",
		re.MULTILINE,
	)
	match = heading.search(text)
	if match is None:
		raise SystemExit(f"changelog.md has no section for {version}")
	rest = text[match.end() :]
	next_heading = re.search(r"^# Norlay Link Checker ", rest, re.MULTILINE)
	body = rest[: next_heading.start()] if next_heading else rest
	body = body.strip()
	if not body:
		raise SystemExit(f"the changelog section for {version} is empty")
	return (
		f"Norlay Link Checker {version}\n\n{body}\n\n"
		"Install the `.nvda-addon` file, or use NVDA's Add-on Store, Install "
		"from external source. The `.zip` contains the same files. "
		"`SHA256SUMS.txt` verifies the download."
	)


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("version", help="for example 1.1.4")
	arguments = parser.parse_args()
	print(section(arguments.version))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
