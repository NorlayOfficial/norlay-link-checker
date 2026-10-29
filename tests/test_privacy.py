"""Static and runtime checks that the privacy promise is kept.

The add-on now talks to Google Gemini, so exactly one file is allowed to use the
network, and exactly one may use ``ctypes`` to encrypt the key.  Anything else
that imports a network, process or file-writing module fails these tests.
"""

import ast
import contextlib
import io
import os
import unittest

from _norlay_link_checker import analyze, render_report

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_ROOT = os.path.join(PROJECT_ROOT, "addon")
CORE_ROOT = os.path.join(ADDON_ROOT, "globalPlugins", "_norlay_link_checker")
ADAPTER_ROOT = os.path.join(ADDON_ROOT, "globalPlugins", "norlayLinkChecker")

AI_CLIENT = os.path.join(CORE_ROOT, "ai", "gemini.py")
SECRETS = os.path.join(ADAPTER_ROOT, "secrets.py")
CLIPBOARD = os.path.join(ADAPTER_ROOT, "clipboard.py")
SETTINGS_PANEL = os.path.join(ADAPTER_ROOT, "settings.py")

#: Modules that reach the network or start processes.
NETWORK_IMPORTS = frozenset({
	"socket",
	"ssl",
	"http",
	"urllib",
	"ftplib",
	"smtplib",
	"poplib",
	"imaplib",
	"telnetlib",
	"requests",
	"httpx",
	"aiohttp",
	"webbrowser",
	"socket",
})

#: Modules that can run code, write files or hide behaviour.
PROCESS_IMPORTS = frozenset({
	"subprocess",
	"ctypes",
	"pickle",
	"multiprocessing",
	"asyncio",
	"logging",
	"tempfile",
	"sqlite3",
})

FORBIDDEN_IMPORTS = NETWORK_IMPORTS | PROCESS_IMPORTS

#: The only places these imports are allowed, and why.  ``urllib.parse`` only
#: splits strings, so it is allowed where an address has to be shortened.
ALLOWED_IMPORTS = {
	AI_CLIENT: {"urllib.request", "urllib.error", "urllib.parse", "socket"},
	os.path.join(CORE_ROOT, "ai", "prompt.py"): {"urllib.parse"},
	SECRETS: {"ctypes"},
	CLIPBOARD: {"ctypes"},
	SETTINGS_PANEL: {"webbrowser"},
}

#: The modules that actually open a connection.
NETWORK_CALLS = ("urllib.request", "urllib.error", "socket", "ssl", "http")

#: NVDA modules that the pure core must not depend on.
NVDA_IMPORTS = frozenset({
	"api",
	"ui",
	"gui",
	"wx",
	"scriptHandler",
	"globalPluginHandler",
	"addonHandler",
	"logHandler",
	"config",
	"nvwave",
	"braille",
	"controlTypes",
	"globalVars",
	"winUser",
})

FORBIDDEN_CALLS = frozenset({"eval", "exec", "compile", "__import__"})


def python_files(root: str):
	for directory, _subdirectories, filenames in os.walk(root):
		for filename in filenames:
			if filename.endswith(".py"):
				yield os.path.join(directory, filename)


def parse(path: str) -> ast.Module:
	with open(path, encoding="utf-8") as handle:
		return ast.parse(handle.read(), filename=path)


def imported_modules(tree: ast.Module) -> list[str]:
	"""Every absolute module name imported by *tree*."""
	found = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			for alias in node.names:
				found.append(alias.name)
		elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
			found.append(node.module)
	return found


class ImportTests(unittest.TestCase):
	def test_network_and_process_imports_are_confined(self):
		for path in python_files(ADDON_ROOT):
			allowed = ALLOWED_IMPORTS.get(path, set())
			for name in imported_modules(parse(path)):
				if name in allowed:
					continue
				self.assertNotIn(
					name.split(".")[0],
					FORBIDDEN_IMPORTS,
					f"{path} imports {name}",
				)
	def test_only_the_gemini_client_can_open_a_connection(self):
		for path in python_files(ADDON_ROOT):
			if path == AI_CLIENT:
				continue
			for name in imported_modules(parse(path)):
				for prefix in NETWORK_CALLS:
					self.assertFalse(
						name == prefix or name.startswith(prefix + "."),
						f"{path} imports {name}",
					)

	def test_ctypes_is_confined_to_low_level_modules(self):
		allowed = {SECRETS, CLIPBOARD}
		for path in python_files(ADDON_ROOT):
			if path in allowed:
				continue
			names = imported_modules(parse(path))
			self.assertNotIn("ctypes", names, f"{path} uses ctypes")

	def test_core_does_not_import_nvda(self):
		for path in python_files(CORE_ROOT):
			for name in imported_modules(parse(path)):
				self.assertNotIn(
					name.split(".")[0],
					NVDA_IMPORTS,
					f"{path} imports NVDA module {name}",
				)

	def test_no_dynamic_code_execution(self):
		for path in python_files(ADDON_ROOT):
			for node in ast.walk(parse(path)):
				if not isinstance(node, ast.Call):
					continue
				name = getattr(node.func, "id", None)
				if name is None:
					continue
				self.assertNotIn(name, FORBIDDEN_CALLS, f"{path} calls {name}")

	def test_no_file_writes(self):
		write_flags = set("wax+")
		for path in python_files(ADDON_ROOT):
			for node in ast.walk(parse(path)):
				if not isinstance(node, ast.Call):
					continue
				func = node.func
				if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
					if func.value.id in {"os", "shutil"} and func.attr in {
						"remove",
						"unlink",
						"rmtree",
					}:
						self.fail(f"{path} deletes a file: {func.value.id}.{func.attr}")
					if func.attr in {"write_text", "write_bytes"}:
						self.fail(f"{path} writes a file: {func.attr}")
				if getattr(func, "id", None) != "open":
					continue
				mode = None
				if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
					mode = node.args[1].value
				for keyword in node.keywords:
					if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
						mode = keyword.value.value
				if isinstance(mode, str):
					self.assertFalse(
						write_flags & set(mode),
						f"{path} opens a file for writing: {mode!r}",
					)

	def test_only_standard_library_and_relative_imports(self):
		"""The core must not depend on anything that is not bundled."""
		allowed = {
			"__future__",
			"collections",
			"dataclasses",
			"ipaddress",
			"json",
			"os",
			"re",
			"socket",
			"textwrap",
			"typing",
			"unicodedata",
			"urllib",
		}
		for path in python_files(CORE_ROOT):
			for name in imported_modules(parse(path)):
				self.assertIn(
					name.split(".")[0],
					allowed,
					f"{path} imports {name}",
				)


class LoggingTests(unittest.TestCase):
	def test_checked_address_is_never_written_to_output(self):
		sentinel = "https://sentinel-8f3a.invalid/secret-token"
		buffer = io.StringIO()
		with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
			analysis = analyze(sentinel)
			render_report(analysis)
		self.assertNotIn("sentinel-8f3a", buffer.getvalue())
		self.assertNotIn("secret-token", buffer.getvalue())

	def test_no_print_calls_in_the_add_on(self):
		for path in python_files(ADDON_ROOT):
			for node in ast.walk(parse(path)):
				if isinstance(node, ast.Call):
					self.assertNotEqual(getattr(node.func, "id", None), "print")


if __name__ == "__main__":
	unittest.main()
