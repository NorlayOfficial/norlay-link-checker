"""Check the add-on metadata and the package that build.py produces."""

import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

import build  # noqa: E402
import buildVars  # noqa: E402

VALID_API_VERSIONS = {"2026.1", "2026.2", "2026.3"}


def version_tuple(value: str) -> tuple[int, ...]:
	return tuple(int(part) for part in value.split("."))


class MetadataTests(unittest.TestCase):
	def setUp(self):
		self.info = buildVars.addon_info

	def test_name_is_unique_style_identifier(self):
		self.assertRegex(self.info["addon_name"], r"^[a-zA-Z][a-zA-Z0-9._-]*$")

	def test_version_is_major_minor_patch(self):
		self.assertRegex(self.info["addon_version"], r"^\d+\.\d+\.\d+$")

	def test_nvda_versions_are_valid_and_ordered(self):
		self.assertIn(self.info["addon_minimumNVDAVersion"], VALID_API_VERSIONS)
		self.assertIn(self.info["addon_lastTestedNVDAVersion"], VALID_API_VERSIONS)
		self.assertLessEqual(
			version_tuple(self.info["addon_minimumNVDAVersion"]),
			version_tuple(self.info["addon_lastTestedNVDAVersion"]),
		)

	def test_urls_are_https(self):
		self.assertTrue(self.info["addon_url"].startswith("https://"))
		self.assertTrue(self.info["addon_sourceURL"].startswith("https://"))
		self.assertTrue(self.info["addon_licenseURL"].startswith("https://"))

	def test_documentation_exists(self):
		path = PROJECT_ROOT / "addon" / "doc" / "en" / self.info["addon_docFileName"]
		self.assertTrue(path.is_file(), path)

	def test_no_placeholder_is_left_in_the_manifest(self):
		text = build.render_manifest(self.info)
		self.assertNotIn("{", text)
		self.assertNotIn("}", text)
		self.assertIn("name = norlayLinkChecker", text)
		self.assertIn("minimumNVDAVersion = 2026.1", text)
		self.assertIn("lastTestedNVDAVersion = 2026.3", text)
		self.assertIn("updateChannel = None", text)


class PackageTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.temporary_directory = tempfile.TemporaryDirectory()
		cls.target = build.build(Path(cls.temporary_directory.name))
		with zipfile.ZipFile(cls.target) as archive:
			cls.names = archive.namelist()
			cls.manifest = archive.read("manifest.ini").decode("utf-8")

	@classmethod
	def tearDownClass(cls):
		cls.temporary_directory.cleanup()

	def test_file_has_the_expected_name(self):
		self.assertEqual(
			self.target.name,
			f"{buildVars.addon_info['addon_name']}-{buildVars.addon_info['addon_version']}.nvda-addon",
		)

	def test_manifest_is_at_the_archive_root(self):
		self.assertIn("manifest.ini", self.names)

	def test_required_parts_are_present(self):
		for name in (
			"globalPlugins/norlayLinkChecker/__init__.py",
			"globalPlugins/norlayLinkChecker/clipboard.py",
			"globalPlugins/norlayLinkChecker/messages.py",
			"globalPlugins/norlayLinkChecker/reportWindow.py",
			"globalPlugins/norlayLinkChecker/resultDialog.py",
			"globalPlugins/norlayLinkChecker/secrets.py",
			"globalPlugins/norlayLinkChecker/settings.py",
			"globalPlugins/norlayLinkChecker/store.py",
			"globalPlugins/_norlay_link_checker/analyzer.py",
			"globalPlugins/_norlay_link_checker/ai/gemini.py",
			"globalPlugins/_norlay_link_checker/data/public_suffix_list.dat",
			"doc/en/readme.html",
		):
			with self.subTest(name=name):
				self.assertIn(name, self.names)

	def test_no_build_artefacts_are_packaged(self):
		for name in self.names:
			with self.subTest(name=name):
				self.assertNotIn("__pycache__", name)
				self.assertFalse(name.endswith(".pyc"))

	def test_manifest_contains_the_metadata(self):
		for key in (
			"name",
			"summary",
			"description",
			"author",
			"version",
			"changelog",
			"docFileName",
			"minimumNVDAVersion",
			"lastTestedNVDAVersion",
			"updateChannel",
		):
			with self.subTest(key=key):
				self.assertRegex(self.manifest, rf"(?m)^{key} = ")
		self.assertRegex(
			self.manifest,
			rf"(?m)^version = {re.escape(buildVars.addon_info['addon_version'])}$",
		)

	def test_manifest_is_the_first_archive_entry(self):
		self.assertEqual(self.names[0], "manifest.ini")

	def test_no_editor_leftovers_are_packaged(self):
		for name in self.names:
			with self.subTest(name=name):
				self.assertNotIn(".DS_Store", name)
				self.assertNotIn("Thumbs.db", name)
				self.assertNotIn("desktop.ini", name)

	def test_zip_copy_matches_the_addon_file(self):
		zip_copy = self.target.with_suffix(".zip")
		self.assertTrue(zip_copy.is_file())
		self.assertEqual(zip_copy.read_bytes(), self.target.read_bytes())

	def test_archive_is_deterministic(self):
		with tempfile.TemporaryDirectory() as other:
			second = build.build(Path(other))
			self.assertEqual(self.target.read_bytes(), second.read_bytes())


class ExclusionTests(unittest.TestCase):
	"""Guard the filter that keeps junk out of the archive."""

	def test_junk_names_are_excluded(self):
		stage = Path("/stage")
		for name in ("__pycache__", ".DS_Store", "Thumbs.db", "desktop.ini", "module.pyc"):
			with self.subTest(name=name):
				path = stage / "globalPlugins" / "pkg" / name
				self.assertTrue(build._is_excluded(path, stage))

	def test_source_files_are_kept(self):
		stage = Path("/stage")
		path = stage / "globalPlugins" / "pkg" / "module.py"
		self.assertFalse(build._is_excluded(path, stage))

	def test_byte_code_left_in_the_source_tree_is_not_packaged(self):
		# Running the test suite imports the add-on, which writes __pycache__.
		# A build after that must still produce a clean archive.
		stray = PROJECT_ROOT / "addon" / "globalPlugins" / "norlayLinkChecker" / "__pycache__"
		stray.mkdir(exist_ok=True)
		(stray / "probe.cpython-314.pyc").write_bytes(b"stale")
		try:
			with tempfile.TemporaryDirectory() as directory:
				target = build.build(Path(directory))
				with zipfile.ZipFile(target) as archive:
					names = archive.namelist()
		finally:
			shutil.rmtree(stray, ignore_errors=True)
		self.assertFalse(
			[name for name in names if "__pycache__" in name or name.endswith(".pyc")],
		)


if __name__ == "__main__":
	unittest.main()
