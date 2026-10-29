#!/usr/bin/env python3
# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Check the built .nvda-addon and its .zip twin.

Used by CI and by hand after a build.  It reads only what the build produced,
so a green result means the file on disk is the file people will install.
"""

from __future__ import annotations

import configparser
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import buildVars  # noqa: E402

REQUIRED = (
	"manifest.ini",
	"doc/en/readme.html",
	"globalPlugins/norlayLinkChecker/__init__.py",
	"globalPlugins/norlayLinkChecker/clipboard.py",
	"globalPlugins/norlayLinkChecker/settings.py",
)


def main() -> int:
	info = buildVars.addon_info
	stem = ROOT / "dist" / f"{info['addon_name']}-{info['addon_version']}"
	addon = Path(str(stem) + ".nvda-addon")
	copy = Path(str(stem) + ".zip")

	if not addon.is_file():
		raise SystemExit(f"missing {addon}")
	if not copy.is_file():
		raise SystemExit(f"missing {copy}")
	if addon.read_bytes() != copy.read_bytes():
		raise SystemExit("the .zip is not identical to the .nvda-addon")

	with zipfile.ZipFile(addon) as archive:
		broken = archive.testzip()
		if broken is not None:
			raise SystemExit(f"corrupt entry: {broken}")
		names = set(archive.namelist())
		text = archive.read("manifest.ini").decode("utf-8")

	missing = [name for name in REQUIRED if name not in names]
	if missing:
		raise SystemExit("missing from the archive: " + ", ".join(missing))
	if any(name.endswith(".pyc") for name in names):
		raise SystemExit("byte-code was packaged")
	if any(name.startswith(".") for name in names):
		raise SystemExit("a dot file was packaged")

	parser = configparser.ConfigParser(interpolation=None)
	parser.read_string("[manifest]\n" + text)
	manifest = parser["manifest"]
	for field in ("name", "summary", "version", "author", "description", "changelog"):
		if not manifest.get(field, "").strip():
			raise SystemExit(f"manifest.ini has an empty {field}")
	if manifest["name"] != info["addon_name"]:
		raise SystemExit("manifest name does not match buildVars.py")
	if manifest["version"] != info["addon_version"]:
		raise SystemExit("manifest version does not match buildVars.py")
	if "{" in text or "}" in text:
		raise SystemExit("manifest.ini still contains placeholders")

	digest = hashlib.sha256(addon.read_bytes()).hexdigest()
	print(f"Add-on: {addon.relative_to(ROOT)}")
	print(f"Size:   {addon.stat().st_size} bytes")
	print(f"SHA256: {digest}")
	print("Zip:    identical")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
