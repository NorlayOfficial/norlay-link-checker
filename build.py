#!/usr/bin/env python3
# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Build a local .nvda-addon file.

This is intentionally small and dependency free.  The resulting package has
the layout NVDA expects: manifest.ini at the archive root, plus doc and
globalPlugins folders.

The build refuses to produce an archive that is obviously broken:

* a required file is missing,
* the manifest still contains template placeholders,
* the manifest is not valid INI or does not match buildVars.py,
* editor or byte-code leftovers would be packed.

Usage:
    python3 build.py
    python3 build.py --output /some/folder
"""

from __future__ import annotations

import argparse
import configparser
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import buildVars  # noqa: E402

# Fixed timestamps keep repeated builds byte-identical.
_ZIP_DATE = (2026, 1, 1, 0, 0, 0)

# Never ship these, whatever a source tree happens to contain.
_EXCLUDED_DIRECTORY_NAMES = {"__pycache__", ".git", ".github", ".vscode", ".idea"}
_EXCLUDED_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

# Paths NVDA needs, relative to the archive root.
_REQUIRED_FILES = (
	"manifest.ini",
	"doc/en/readme.html",
	"globalPlugins/norlayLinkChecker/__init__.py",
	"globalPlugins/norlayLinkChecker/clipboard.py",
	"globalPlugins/norlayLinkChecker/messages.py",
	"globalPlugins/norlayLinkChecker/reportWindow.py",
	"globalPlugins/norlayLinkChecker/resultDialog.py",
	"globalPlugins/norlayLinkChecker/secrets.py",
	"globalPlugins/norlayLinkChecker/settings.py",
	"globalPlugins/norlayLinkChecker/store.py",
	"globalPlugins/_norlay_link_checker/__init__.py",
	"globalPlugins/_norlay_link_checker/ai/gemini.py",
	"globalPlugins/_norlay_link_checker/data/public_suffix_list.dat",
)


class BuildError(Exception):
	"""The staged add-on would not be usable by NVDA."""


def render_manifest(info: dict) -> str:
	template = (ROOT / "manifest.ini.tpl").read_text(encoding="utf-8")
	values = dict(info)
	if values.get("addon_updateChannel") is None:
		values["addon_updateChannel"] = "None"
	return template.format(**values)


def _is_excluded(path: Path, stage: Path) -> bool:
	relative = path.relative_to(stage)
	if path.name in _EXCLUDED_DIRECTORY_NAMES or path.name in _EXCLUDED_FILE_NAMES:
		return True
	if any(part in _EXCLUDED_DIRECTORY_NAMES for part in relative.parts[:-1]):
		return True
	return path.suffix.lower() in _EXCLUDED_SUFFIXES


def _stage(info: dict) -> Path:
	stage = ROOT / "build" / "addon"
	if stage.exists():
		shutil.rmtree(stage)
	shutil.copytree(ROOT / "addon", stage)

	# Deepest paths first so deleting a directory cannot invalidate a later entry.
	entries = sorted(stage.rglob("*"), key=lambda path: len(path.parts), reverse=True)
	for path in entries:
		if _is_excluded(path, stage):
			if path.is_dir():
				shutil.rmtree(path)
			elif path.exists():
				path.unlink()

	(stage / "manifest.ini").write_text(render_manifest(info), encoding="utf-8")
	_validate_stage(stage, info)
	return stage


def _validate_stage(stage: Path, info: dict) -> None:
	"""Fail the build instead of handing out a package NVDA would reject."""
	missing = [name for name in _REQUIRED_FILES if not (stage / name).is_file()]
	if missing:
		raise BuildError("missing required file(s): " + ", ".join(missing))

	text = (stage / "manifest.ini").read_text(encoding="utf-8")
	if text.startswith("\ufeff"):
		raise BuildError("manifest.ini starts with a byte order mark")
	if "{" in text or "}" in text:
		raise BuildError("manifest.ini still contains template placeholders")

	# The manifest has no section header, so give ConfigParser a temporary one.
	parser = configparser.ConfigParser(interpolation=None)
	try:
		parser.read_string("[manifest]\n" + text)
	except configparser.Error as error:
		raise BuildError(f"manifest.ini is not valid INI: {error}") from error
	manifest = parser["manifest"]

	for field in ("name", "summary", "version", "author", "description", "changelog"):
		if not manifest.get(field, "").strip():
			raise BuildError(f"manifest.ini has an empty {field}")
	if manifest["name"] != info["addon_name"]:
		raise BuildError("manifest name does not match buildVars.addon_name")
	if manifest["version"] != info["addon_version"]:
		raise BuildError("manifest version does not match buildVars.addon_version")

	minimum = tuple(int(part) for part in manifest["minimumNVDAVersion"].split("."))
	last_tested = tuple(int(part) for part in manifest["lastTestedNVDAVersion"].split("."))
	if minimum > last_tested:
		raise BuildError("minimumNVDAVersion is newer than lastTestedNVDAVersion")

	for path in stage.rglob("*"):
		if path.is_file() and _is_excluded(path, stage):
			raise BuildError(f"excluded file would be packaged: {path.relative_to(stage)}")


def _add_file(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
	entry = zipfile.ZipInfo(arcname, date_time=_ZIP_DATE)
	entry.compress_type = zipfile.ZIP_DEFLATED
	entry.external_attr = 0o644 << 16
	archive.writestr(entry, path.read_bytes())


def build(output_directory: Path | None = None) -> Path:
	info = buildVars.addon_info
	stage = _stage(info)

	output_directory = output_directory or (ROOT / "dist")
	output_directory.mkdir(parents=True, exist_ok=True)
	stem = f"{info['addon_name']}-{info['addon_version']}"
	target = output_directory / f"{stem}.nvda-addon"
	if target.exists():
		target.unlink()

	files = sorted(path for path in stage.rglob("*") if path.is_file())
	manifest = stage / "manifest.ini"
	files.remove(manifest)
	files.insert(0, manifest)

	with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
		for path in files:
			_add_file(archive, path, path.relative_to(stage).as_posix())

	# The same bytes with a .zip ending, for the manual "extract into the
	# add-ons folder" route.  Explorer handles .zip without any file
	# association to NVDA, which makes it the reliable fallback on Windows.
	zip_copy = output_directory / f"{stem}.zip"
	shutil.copyfile(target, zip_copy)

	return target


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--output",
		type=Path,
		default=None,
		help="folder for the .nvda-addon file (default: dist/)",
	)
	arguments = parser.parse_args()
	target = build(arguments.output)
	digest = hashlib.sha256(target.read_bytes()).hexdigest()
	print(f"Built:  {target}")
	print(f"Copy:   {target.with_suffix('.zip')}")
	print(f"Size:   {target.stat().st_size} bytes")
	print(f"SHA256: {digest}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
