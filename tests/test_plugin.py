"""Integration tests for the NVDA-facing adapter.

NVDA itself cannot run here, so the NVDA modules the adapter uses are replaced
with small stubs.  The real plugin code still runs: the gesture functions, the
Tools menu wiring, the clipboard paths, the consent gate, the background request
seam and the read-only window.
"""

import builtins
import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ADDON_ROOT = PROJECT_ROOT / "addon"
PLUGINS_ROOT = ADDON_ROOT / "globalPlugins"
for path in (str(ADDON_ROOT), str(PLUGINS_ROOT)):
	if path not in sys.path:
		sys.path.insert(0, path)


class _MenuItem:
	def __init__(self, label, help_text):
		self.label = label
		self.help_text = help_text
		self.destroyed = False

	def Destroy(self):
		self.destroyed = True


class _Menu:
	def __init__(self):
		self.items = []

	def Append(self, identifier, label, help_text=""):
		item = _MenuItem(label, help_text)
		self.items.append(item)
		return item

	def Remove(self, item):
		self.items.remove(item)


class _TrayIcon:
	def __init__(self):
		self.toolsMenu = _Menu()
		self.bindings = []

	def Bind(self, event, handler, source):
		self.bindings.append((event, handler, source))

	def Unbind(self, event, handler, source):
		self.bindings = [
			binding
			for binding in self.bindings
			if binding != (event, handler, source)
		]


class _Font:
	def SetFaceName(self, name):
		self.face = name


class _TextCtrl:
	def __init__(self, parent=None, identifier=-1, value="", style=0, **kwargs):
		self.parent = parent
		self.value = value
		self.style = style
		self.focused = False
		self.insertion_point = 0
		self.font = _Font()
		self.name = ""

	def GetValue(self):
		return self.value

	def SetValue(self, value):
		self.value = value

	def SetLabel(self, label):
		self.value = label

	def SetInsertionPoint(self, position):
		self.insertion_point = position

	def GetFont(self):
		return self.font

	def SetFont(self, font):
		self.font = font

	def SetFocus(self):
		self.focused = True

	def SetMinSize(self, size):
		self.min_size = size

	def SetName(self, name):
		self.name = name


class _Button:
	def __init__(self, parent=None, identifier=-1, label="", **kwargs):
		self.parent = parent
		self.identifier = identifier
		self.label = label
		self.default = False
		self.enabled = True
		self.bindings = []

	def Bind(self, event, handler):
		self.bindings.append((event, handler))

	def SetDefault(self):
		self.default = True

	def Disable(self):
		self.enabled = False

	def Enable(self):
		self.enabled = True


class _Dialog:
	instances = []

	def __init__(self, parent=None, identifier=-1, title="", style=0, **kwargs):
		self.parent = parent
		self.identifier = identifier
		self.title = title
		self.style = style
		self.sizer = None
		self.destroyed = False
		self.modal = False
		self.ended = None
		self.escape_id = None
		self.affirmative_id = None
		_Dialog.instances.append(self)

	def SetSizer(self, sizer):
		self.sizer = sizer

	def SetEscapeId(self, identifier):
		self.escape_id = identifier

	def SetAffirmativeId(self, identifier):
		self.affirmative_id = identifier

	def ShowModal(self):
		self.modal = True
		return self.ended

	def EndModal(self, identifier):
		self.ended = identifier

	def Destroy(self):
		self.destroyed = True


class _Frame:
	def __init__(self, parent=None, identifier=-1, title="", style=0, **kwargs):
		self.parent = parent
		self.title = title
		self.style = style
		self.shown = False
		self.raised = False
		self.destroyed = False
		self.bindings = []
		self.sizer = None

	def SetTitle(self, title):
		self.title = title

	def GetTitle(self):
		return self.title

	def SetMinSize(self, size):
		self.min_size = size

	def SetSizer(self, sizer):
		self.sizer = sizer

	def Bind(self, event, handler):
		self.bindings.append((event, handler))

	def Show(self):
		self.shown = True

	def Hide(self):
		self.shown = False

	def Raise(self):
		self.raised = True

	def Destroy(self):
		self.destroyed = True


class _BoxSizer:
	def __init__(self, orientation=0):
		self.orientation = orientation
		self.children = []

	def Add(self, widget, proportion=0, flag=0, border=0):
		self.children.append(widget)


class _KeyEvent:
	def __init__(self, key):
		self.key = key
		self.skipped = False

	def GetKeyCode(self):
		return self.key

	def Skip(self):
		self.skipped = True


class _InlineThread:
	"""Run the target while start() is called, so tests need no threads."""

	def __init__(self, target, daemon=False):
		self.target = target
		self.daemon = daemon

	def start(self):
		self.target()


class _MessageDialog:
	def __init__(self, parent, message, caption="", style=0):
		self.message = message
		self.caption = caption
		self.style = style
		self.destroyed = False

	def SetYesNoLabels(self, yes, no):
		self.labels = (yes, no)

	def ShowModal(self):
		return recorder.consent_answer

	def Destroy(self):
		self.destroyed = True


class _Recorder:
	def __init__(self):
		self.reset()

	def reset(self):
		self.messages = []
		self.windows = []
		self.debug = []
		self.clipboard = ""
		self.clipboard_error = None
		self.consent_answer = 1
		self.consent_dialogs = []
		self.settings_opened = 0
		self.requests = []


recorder = _Recorder()


class _Conf:
	def __init__(self):
		self.spec = {}
		self.sections = {}

	def __getitem__(self, name):
		if name not in self.sections:
			self.sections[name] = {
				"apiKey": "",
				"model": "gemini-3.5-flash-lite",
				"timeout": 25,
				"includeQuery": True,
				"consented": False,
			}
		return self.sections[name]


def _install_stubs():
	addon_handler = types.ModuleType("addonHandler")

	def init_translation():
		builtins._ = lambda message: message

	addon_handler.initTranslation = init_translation

	global_plugin_handler = types.ModuleType("globalPluginHandler")

	class GlobalPlugin:
		def __init__(self):
			pass

		def terminate(self):
			pass

	global_plugin_handler.GlobalPlugin = GlobalPlugin

	script_handler = types.ModuleType("scriptHandler")

	def script(**metadata):
		def decorator(function):
			function.script_metadata = metadata
			return function

		return decorator

	script_handler.script = script

	ui = types.ModuleType("ui")

	def message(text):
		recorder.messages.append(text)

	ui.message = message

	settings_dialogs = types.ModuleType("gui.settingsDialogs")

	class SettingsPanel:
		title = ""

		def __init__(self, parent=None):
			self.parent = parent

	class NVDASettingsDialog:
		categoryClasses = []

	settings_dialogs.SettingsPanel = SettingsPanel
	settings_dialogs.NVDASettingsDialog = NVDASettingsDialog

	gui = types.ModuleType("gui")
	gui.mainFrame = types.SimpleNamespace(
		sysTrayIcon=_TrayIcon(),
	)
	gui.settingsDialogs = settings_dialogs

	def popup_settings(*args, **kwargs):
		recorder.settings_opened += 1

	gui.mainFrame.popupSettingsDialog = popup_settings

	wx = types.ModuleType("wx")
	wx.ID_ANY = -1
	wx.EVT_MENU = "evt-menu"
	wx.EVT_CLOSE = "evt-close"
	wx.EVT_BUTTON = "evt-button"
	wx.EVT_CHAR_HOOK = "evt-char-hook"
	wx.WXK_ESCAPE = 27
	wx.ID_CLOSE = 5100
	wx.DEFAULT_FRAME_STYLE = 0
	wx.DEFAULT_DIALOG_STYLE = 0
	wx.VERTICAL = 0
	wx.HORIZONTAL = 1
	wx.EXPAND = 1
	wx.ALL = 2
	wx.LEFT = 4
	wx.RIGHT = 8
	wx.TOP = 16
	wx.BOTTOM = 32
	wx.ALIGN_RIGHT = 64
	wx.TE_MULTILINE = 32
	wx.TE_READONLY = 16
	wx.TE_RICH = 64
	wx.TE_PASSWORD = 128
	wx.YES_NO = 8
	wx.ICON_QUESTION = 16
	wx.ICON_ERROR = 32
	wx.OK = 4
	wx.YES = 1
	wx.NO = 0
	wx.ID_YES = 1
	wx.ID_NO = 0
	wx.Frame = _Frame
	wx.Dialog = _Dialog
	wx.TextCtrl = _TextCtrl
	wx.Button = _Button
	wx.BoxSizer = _BoxSizer

	def call_after(function, *args):
		return function(*args)

	wx.CallAfter = call_after

	def message_dialog(parent, message, caption="", style=0):
		dialog = _MessageDialog(parent, message, caption, style)
		recorder.consent_dialogs.append(dialog)
		return dialog

	wx.MessageDialog = message_dialog

	log_handler = types.ModuleType("logHandler")

	class _Log:
		def debug(self, message, *args, **kwargs):
			recorder.debug.append(message % args if args else message)

		def error(self, message, *args, **kwargs):
			recorder.debug.append(message % args if args else message)

	log_handler.log = _Log()

	api = types.ModuleType("api")

	def get_clip_data():
		if recorder.clipboard_error is not None:
			raise recorder.clipboard_error
		return recorder.clipboard

	api.getClipData = get_clip_data

	config = types.ModuleType("config")
	config.conf = _Conf()

	for name, module in {
		"addonHandler": addon_handler,
		"globalPluginHandler": global_plugin_handler,
		"scriptHandler": script_handler,
		"ui": ui,
		"gui": gui,
		"wx": wx,
		"logHandler": log_handler,
		"api": api,
		"config": config,
	}.items():
		sys.modules[name] = module


_install_stubs()

import globalPlugins.norlayLinkChecker as plugin_module  # noqa: E402
from globalPlugins.norlayLinkChecker import (  # noqa: E402
	clipboard,
	reportWindow,
	resultDialog,
	settings,
	store,
)
from _norlay_link_checker.ai import GeminiError  # noqa: E402

ANSWER = "This looks like the account area of example.com."


def _sync_run(work, on_success, on_error):
	try:
		result = work()
	except Exception as error:  # noqa: BLE001
		on_error(error)
	else:
		on_success(result)


class PluginTestCase(unittest.TestCase):
	def setUp(self):
		recorder.reset()
		_Dialog.instances.clear()
		recorder.clipboard = "https://example.com/account"
		store.protect = lambda text: text
		store.unprotect = lambda value: value
		store.set_api_key("test-key")
		store.set_consented(True)
		store.set_include_query(True)
		store.set_model("gemini-3.5-flash-lite")
		plugin_module._cache.clear()

		self.original_run = plugin_module._run_in_background
		self.original_explain = plugin_module.explain
		self.original_show = plugin_module.show_report
		plugin_module._run_in_background = _sync_run
		plugin_module.explain = self._fake_explain
		plugin_module.show_report = lambda title, text: recorder.windows.append(
			{"title": title, "text": text},
		)
		self.plugin = plugin_module.GlobalPlugin()

	def tearDown(self):
		self.plugin.terminate()
		plugin_module._run_in_background = self.original_run
		plugin_module.explain = self.original_explain
		plugin_module.show_report = self.original_show
		reportWindow.close_report()

	def _fake_explain(self, url, facts, key, model, timeout=25, transport=None):
		recorder.requests.append(
			{"url": url, "facts": list(facts), "model": model, "timeout": timeout},
		)
		return ANSWER


class MenuAndSettingsTests(PluginTestCase):
	def test_tools_menu_item_is_added_and_removed(self):
		tray_icon = plugin_module.gui.mainFrame.sysTrayIcon
		self.assertEqual(len(tray_icon.toolsMenu.items), 1)
		self.assertEqual(tray_icon.toolsMenu.items[0].label, "Explain link in clipboard")
		self.plugin.terminate()
		self.assertEqual(tray_icon.toolsMenu.items, [])

	def test_settings_panel_is_registered_and_removed(self):
		categories = plugin_module.gui.settingsDialogs.NVDASettingsDialog.categoryClasses
		self.assertIn(plugin_module.NorlaySettingsPanel, categories)
		self.plugin.terminate()
		self.assertNotIn(plugin_module.NorlaySettingsPanel, categories)


class ReportFlowTests(PluginTestCase):
	def test_explanation_appears_in_the_read_only_window(self):
		self.plugin.script_explainLinkInClipboard(None)
		self.assertGreaterEqual(len(recorder.windows), 1)
		window = recorder.windows[-1]
		self.assertIn(ANSWER, window["text"])
		self.assertIn("https://example.com/account", window["text"])
		self.assertIn("not a safety check", window["text"])
		self.assertIn("example.com", window["title"])
		self.assertEqual(recorder.messages, [])

	def test_loading_state_is_shown_before_the_answer(self):
		seen = []
		original = plugin_module.show_report
		plugin_module.show_report = lambda title, text: seen.append(text)
		try:
			self.plugin.script_explainLinkInClipboard(None)
		finally:
			plugin_module.show_report = original
		self.assertEqual(len(seen), 2)
		self.assertIn("Checking with Gemini", seen[0])
		self.assertIn(ANSWER, seen[1])

	def test_second_check_of_the_same_link_costs_no_quota(self):
		self.plugin.script_explainLinkInClipboard(None)
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(len(recorder.requests), 1)
		self.assertIn(ANSWER, recorder.windows[-1]["text"])

	def test_query_string_can_be_left_out(self):
		store.set_include_query(False)
		recorder.clipboard = "https://example.com/account?token=abc#top"
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(recorder.requests[0]["url"], "https://example.com/account")

	def test_speak_only_script_does_not_open_a_window(self):
		self.plugin.script_speakLinkExplanation(None)
		self.assertEqual(recorder.windows, [])
		self.assertEqual(recorder.messages, [ANSWER])

	def test_facts_are_token_cheap_codes(self):
		self.plugin.script_explainLinkInClipboard(None)
		facts = recorder.requests[0]["facts"]
		self.assertIn("scheme=https", facts)
		self.assertIn("registrable=example.com", facts)


class SetupAndConsentTests(PluginTestCase):
	def test_missing_key_explains_and_opens_settings(self):
		store.set_api_key("")
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(recorder.requests, [])
		self.assertEqual(recorder.settings_opened, 1)
		self.assertIn("free Gemini API key", recorder.messages[0])

	def test_declining_consent_sends_nothing(self):
		store.set_consented(False)
		recorder.consent_answer = 0
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(recorder.requests, [])
		self.assertEqual(recorder.windows, [])
		self.assertEqual(len(recorder.consent_dialogs), 1)

	def test_accepting_consent_is_remembered(self):
		store.set_consented(False)
		recorder.consent_answer = 1
		self.plugin.script_explainLinkInClipboard(None)
		self.assertTrue(store.consented())
		self.assertEqual(len(recorder.requests), 1)

	def test_consent_text_names_google(self):
		store.set_consented(False)
		recorder.consent_answer = 0
		self.plugin.script_explainLinkInClipboard(None)
		message = recorder.consent_dialogs[0].message
		self.assertIn("Google Gemini", message)
		self.assertIn("generativelanguage.googleapis.com", message)


class FailureTests(PluginTestCase):
	def test_quota_failure_is_explained_in_the_window(self):
		def failing(*args, **kwargs):
			recorder.requests.append({"url": args[0]})
			raise GeminiError("quota")

		plugin_module.explain = failing
		self.plugin.script_explainLinkInClipboard(None)
		self.assertIn("quota", recorder.windows[-1]["text"])

	def test_auth_failure_is_explained(self):
		def failing(*args, **kwargs):
			raise GeminiError("auth")

		plugin_module.explain = failing
		self.plugin.script_speakLinkExplanation(None)
		self.assertIn("API key", recorder.messages[0])

	def test_empty_clipboard(self):
		recorder.clipboard = ""
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(
			recorder.messages,
			["The clipboard is empty. Copy a link and try again."],
		)

	def test_clipboard_without_a_link_shows_a_window(self):
		recorder.clipboard = "nothing to see here"
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(recorder.requests, [])
		self.assertEqual(recorder.messages, [])
		self.assertIn("not a link", recorder.windows[-1]["text"])
		self.assertEqual(recorder.windows[-1]["title"], "Norlay Link Checker")

	def test_clipboard_without_a_link_is_spoken_when_speech_only(self):
		recorder.clipboard = "nothing to see here"
		self.plugin.script_speakLinkExplanation(None)
		self.assertEqual(recorder.windows, [])
		self.assertIn("not a link", recorder.messages[0])

	def test_a_file_name_is_not_sent_as_a_link(self):
		recorder.clipboard = "report.pdf"
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(recorder.requests, [])
		self.assertIn("not a link", recorder.windows[-1]["text"])

	def test_dotted_words_are_not_sent_as_links(self):
		for text in ("hello.there", "my notes.txt", "photo.jpg"):
			with self.subTest(text=text):
				recorder.reset()
				store.set_api_key("test-key")
				recorder.clipboard = text
				self.plugin.script_explainLinkInClipboard(None)
				self.assertEqual(recorder.requests, [])

	def test_copied_files_are_reported_as_files(self):
		original = clipboard._clipboard_kind
		clipboard._clipboard_kind = lambda: "files"
		self.addCleanup(setattr, clipboard, "_clipboard_kind", original)
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(recorder.requests, [])
		self.assertEqual(recorder.messages, [])
		text = recorder.windows[-1]["text"]
		self.assertIn("holds a file", text)
		self.assertNotIn("Another app", text)

	def test_copied_files_are_spoken_when_speech_only(self):
		original = clipboard._clipboard_kind
		clipboard._clipboard_kind = lambda: "files"
		self.addCleanup(setattr, clipboard, "_clipboard_kind", original)
		self.plugin.script_speakLinkExplanation(None)
		self.assertEqual(recorder.windows, [])
		self.assertIn("holds a file", recorder.messages[0])

	def test_a_picture_is_not_called_a_link(self):
		original = clipboard._clipboard_kind
		clipboard._clipboard_kind = lambda: "other"
		self.addCleanup(setattr, clipboard, "_clipboard_kind", original)
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(recorder.requests, [])
		self.assertIn("not text", recorder.windows[-1]["text"])

	def test_empty_clipboard_format_is_reported_as_empty(self):
		original = clipboard._clipboard_kind
		clipboard._clipboard_kind = lambda: "empty"
		self.addCleanup(setattr, clipboard, "_clipboard_kind", original)
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(recorder.messages, ["The clipboard is empty. Copy a link and try again."])

	def test_clipboard_error_is_explained(self):
		recorder.clipboard_error = OSError("busy")
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(
			recorder.messages,
			["Another app is using the clipboard. Try again in a moment."],
		)

	def test_malformed_ipv6_is_explained(self):
		recorder.clipboard = "https://2001:db8::1/path"
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(
			recorder.messages,
			["An IPv6 address must be enclosed in square brackets."],
		)

	def test_clipboard_is_never_written_back(self):
		before = recorder.clipboard
		self.plugin.script_explainLinkInClipboard(None)
		self.assertEqual(recorder.clipboard, before)

	def test_the_address_never_reaches_the_log(self):
		recorder.clipboard = "https://sentinel-8f3a.invalid/private?token=abc"
		self.plugin.script_explainLinkInClipboard(None)
		for entry in recorder.debug:
			self.assertNotIn("sentinel-8f3a", entry)
			self.assertNotIn("token", entry)


class ReadOnlyWindowTests(PluginTestCase):
	def test_window_uses_a_read_only_text_field(self):
		reportWindow.show_report("Title", "Body text")
		window = reportWindow._window
		self.assertIsNotNone(window)
		self.assertTrue(window.text.style & plugin_module.wx.TE_READONLY)
		self.assertTrue(window.text.style & plugin_module.wx.TE_MULTILINE)
		self.assertEqual(window.text.GetValue(), "Body text")
		self.assertTrue(window.text.focused)
		self.assertTrue(window.shown)

	def test_window_has_a_close_button(self):
		reportWindow.show_report("Title", "Body")
		window = reportWindow._window
		self.assertEqual(window.closeButton.label, "Close")
		self.assertIn((plugin_module.wx.EVT_BUTTON, window._on_close_button), window.closeButton.bindings)
		window.closeButton.bindings[0][1](None)
		self.assertFalse(window.shown)

	def test_escape_hides_the_window(self):
		reportWindow.show_report("Title", "Body")
		window = reportWindow._window
		event = _KeyEvent(plugin_module.wx.WXK_ESCAPE)
		window._on_char_hook(event)
		self.assertFalse(window.shown)
		self.assertFalse(event.skipped)

	def test_other_keys_reach_the_text_field(self):
		reportWindow.show_report("Title", "Body")
		window = reportWindow._window
		event = _KeyEvent(ord("A"))
		window._on_char_hook(event)
		self.assertTrue(window.shown)
		self.assertTrue(event.skipped)


	def test_window_is_reused_and_updated(self):
		reportWindow.show_report("First", "one")
		first = reportWindow._window
		reportWindow.show_report("Second", "two")
		self.assertIs(reportWindow._window, first)
		self.assertEqual(first.text.GetValue(), "two")
		self.assertEqual(first.GetTitle(), "Second")

	def test_cursor_starts_at_the_top(self):
		reportWindow.show_report("Title", "line one\nline two")
		self.assertEqual(reportWindow._window.text.insertion_point, 0)

	def test_close_report_destroys_the_window(self):
		reportWindow.show_report("Title", "Body")
		window = reportWindow._window
		reportWindow.close_report()
		self.assertIsNone(reportWindow._window)
		self.assertTrue(window.destroyed)


class ClipboardKindTests(unittest.TestCase):
	"""The clipboard reader must distinguish files, text and other formats."""

	def setUp(self):
		recorder.reset()
		self.original = clipboard._clipboard_kind

	def tearDown(self):
		clipboard._clipboard_kind = self.original

	def test_files_raise_their_own_error(self):
		clipboard._clipboard_kind = lambda: "files"
		with self.assertRaises(clipboard.ClipboardHasFiles):
			clipboard.read_clipboard_text()

	def test_other_formats_raise_their_own_error(self):
		clipboard._clipboard_kind = lambda: "other"
		with self.assertRaises(clipboard.ClipboardHasNoText):
			clipboard.read_clipboard_text()

	def test_locked_clipboard_raises_unavailable(self):
		clipboard._clipboard_kind = lambda: "locked"
		with self.assertRaises(clipboard.ClipboardUnavailable):
			clipboard.read_clipboard_text()

	def test_empty_clipboard_returns_empty_text(self):
		clipboard._clipboard_kind = lambda: "empty"
		self.assertEqual(clipboard.read_clipboard_text(), "")

	def test_text_is_returned_unchanged(self):
		clipboard._clipboard_kind = lambda: "text"
		recorder.clipboard = "https://example.com"
		self.assertEqual(clipboard.read_clipboard_text(), "https://example.com")


class ResultDialogTests(unittest.TestCase):
	def setUp(self):
		_Dialog.instances.clear()

	def test_message_is_read_only_and_has_a_close_button(self):
		dialog = resultDialog.ResultDialog(None, "Title", "It worked.")
		self.assertEqual(dialog.title, "Title")
		self.assertEqual(dialog.messageCtrl.GetValue(), "It worked.")
		self.assertTrue(dialog.messageCtrl.style & resultDialog.wx.TE_READONLY)
		self.assertTrue(dialog.messageCtrl.style & resultDialog.wx.TE_MULTILINE)
		self.assertEqual(dialog.closeButton.label, "Close")
		self.assertTrue(dialog.closeButton.default)
		self.assertEqual(dialog.escape_id, resultDialog.wx.ID_CLOSE)
		self.assertEqual(dialog.affirmative_id, resultDialog.wx.ID_CLOSE)
		self.assertTrue(dialog.messageCtrl.focused)

	def test_close_button_ends_the_dialog(self):
		dialog = resultDialog.ResultDialog(None, "Title", "Body")
		self.assertEqual(len(dialog.closeButton.bindings), 1)
		event, handler = dialog.closeButton.bindings[0]
		self.assertEqual(event, resultDialog.wx.EVT_BUTTON)
		handler(None)
		self.assertEqual(dialog.ended, resultDialog.wx.ID_CLOSE)

	def test_show_result_is_modal_and_destroys_the_dialog(self):
		resultDialog.show_result(None, "Title", "Body")
		dialog = _Dialog.instances[-1]
		self.assertTrue(dialog.modal)
		self.assertTrue(dialog.destroyed)
		self.assertEqual(dialog.title, "Title")
		self.assertEqual(dialog.messageCtrl.GetValue(), "Body")


class KeyTestDialogTests(unittest.TestCase):
	"""The Test the key button must report through a dialog, not a label."""

	def setUp(self):
		recorder.reset()
		self.panel = object.__new__(settings.NorlaySettingsPanel)
		self.panel.keyCtrl = _TextCtrl(value="test-key")
		self.panel.modelCtrl = types.SimpleNamespace(GetSelection=lambda: 0)
		self.panel.modelIds = ["gemini-3.5-flash-lite"]
		self.panel.timeoutCtrl = types.SimpleNamespace(GetValue=lambda: 7)
		self.panel.testButton = _Button()
		self.panel.statusCtrl = _TextCtrl()
		self.shown = []
		self.original_show = settings.show_result
		self.original_threading = settings.threading
		self.original_explain = settings.explain
		settings.show_result = lambda *args: self.shown.append(args)
		settings.threading = types.SimpleNamespace(Thread=_InlineThread)
		settings.explain = lambda *args, **kwargs: ANSWER

	def tearDown(self):
		settings.show_result = self.original_show
		settings.threading = self.original_threading
		settings.explain = self.original_explain

	def test_success_opens_a_dialog(self):
		self.panel._on_test(None)
		self.assertEqual(len(self.shown), 1)
		parent, _title, message = self.shown[0]
		self.assertIs(parent, self.panel)
		self.assertEqual(message, "The key works.")
		self.assertTrue(self.panel.testButton.enabled)
		self.assertEqual(self.panel.statusCtrl.GetValue(), "")

	def test_failure_opens_the_error_in_the_same_dialog(self):
		def failing(*args, **kwargs):
			raise settings.GeminiError("auth")

		settings.explain = failing
		self.panel._on_test(None)
		self.assertEqual(len(self.shown), 1)
		self.assertIn("API key", self.shown[0][2])
		self.assertTrue(self.panel.testButton.enabled)

	def test_empty_key_shows_no_dialog(self):
		self.panel.keyCtrl.SetValue("")
		self.panel._on_test(None)
		self.assertEqual(self.shown, [])
		self.assertIn("free Gemini API key", self.panel.statusCtrl.GetValue())


if __name__ == "__main__":
	unittest.main()
