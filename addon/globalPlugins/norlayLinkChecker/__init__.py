# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""NVDA global plugin: clipboard in, Gemini explanation out.

This module is the only part of the add-on that talks to NVDA.  The address
handling and the Gemini client live in the ``globalPlugins._norlay_link_checker``
package, which has no NVDA imports and can be tested on its own.
"""

from __future__ import annotations

import builtins
import threading

import addonHandler

addonHandler.initTranslation()

# initTranslation installs the add-on's gettext function as the builtin ``_``.
_ = builtins._  # noqa: F821

import globalPluginHandler  # noqa: E402
import gui  # noqa: E402
import ui  # noqa: E402
import wx  # noqa: E402
from globalPlugins._norlay_link_checker import (  # noqa: E402
	InvalidURL,
	NoURLFound,
	URLTooLong,
	analyze,
)
from globalPlugins._norlay_link_checker.ai import GeminiError, explain  # noqa: E402
from globalPlugins._norlay_link_checker.ai.prompt import without_query  # noqa: E402
from logHandler import log  # noqa: E402
from scriptHandler import script  # noqa: E402

from . import messages, store  # noqa: E402
from .clipboard import (  # noqa: E402
	ClipboardHasFiles,
	ClipboardHasNoText,
	ClipboardUnavailable,
	read_clipboard_text,
)
from .reportWindow import close_report, show_report  # noqa: E402
from .settings import NorlaySettingsPanel  # noqa: E402

store.register()

_INVALID_MESSAGES = {
	"ipv6_brackets": _(
		"An IPv6 address must be enclosed in square brackets.",
	),
	"ipv6_trailing": _(
		"The part after the IPv6 address is not valid.",
	),
	"no_host": _(
		"That address does not contain a website name.",
	),
}

_INVALID_MESSAGE_DEFAULT = _(
	"That address is not valid. Check that it was copied completely.",
)

_DISCLAIMER = _("This explains the address. It is not a safety check.")

_NOT_A_LINK = _(
	"This is not a link. Copy a web address, such as https://example.com, and "
	"try again.",
)

_FILE_NOT_LINK = _(
	"The clipboard holds a file or folder, not a link. Copy a web address and "
	"try again.",
)

_NO_TEXT = _(
	"The clipboard holds something that is not text, such as an image. Copy a "
	"web address and try again.",
)

#: Answers kept in memory, so pressing the shortcut twice costs no quota.
_CACHE_LIMIT = 32
_cache: dict[str, str] = {}


def _remember(url: str, answer: str) -> None:
	_cache[url] = answer
	while len(_cache) > _CACHE_LIMIT:
		_cache.pop(next(iter(_cache)))


def _run_in_background(work, on_success, on_error) -> None:
	"""Run *work* off the main thread.

	A network call on NVDA's main thread would freeze speech and input, so the
	request always runs in a daemon thread and comes back through
	``wx.CallAfter``.  Tests replace this function with a synchronous one.
	"""

	def runner() -> None:
		try:
			result = work()
		except GeminiError as error:
			wx.CallAfter(on_error, error)
		except Exception:
			wx.CallAfter(on_error, GeminiError("response"))
		else:
			wx.CallAfter(on_success, result)

	threading.Thread(target=runner, daemon=True).start()


def _facts(analysis) -> list[str]:
	"""A token-cheap summary of what is already known locally."""
	parsed = analysis.parsed
	facts: list[str] = []
	if parsed.scheme:
		facts.append(f"scheme={parsed.scheme}")
	if parsed.host:
		facts.append(f"host={parsed.host_ascii or parsed.host}")
	if analysis.host_info is not None:
		facts.append(f"registrable={analysis.host_info.registrable}")
		if analysis.host_info.subdomain:
			facts.append(f"subdomain={analysis.host_info.subdomain}")
	if parsed.is_ip:
		facts.append("host is a raw IP address")
	if parsed.port:
		facts.append(f"port={parsed.port}")
	for finding in analysis.findings[:6]:
		facts.append(finding.code)
	return facts


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Explain the link in the clipboard with Gemini."""

	scriptCategory = _("Norlay Link Checker")

	def __init__(self):
		super().__init__()
		self._toolsMenuItem = None
		self._pending = 0
		self._addToolsMenuItem()
		self._registerSettingsPanel()

	def _registerSettingsPanel(self) -> None:
		categories = gui.settingsDialogs.NVDASettingsDialog.categoryClasses
		if NorlaySettingsPanel not in categories:
			categories.append(NorlaySettingsPanel)

	def _unregisterSettingsPanel(self) -> None:
		categories = gui.settingsDialogs.NVDASettingsDialog.categoryClasses
		while NorlaySettingsPanel in categories:
			categories.remove(NorlaySettingsPanel)

	def _addToolsMenuItem(self) -> None:
		try:
			trayIcon = gui.mainFrame.sysTrayIcon
			if trayIcon is None:
				return
			self._toolsMenuItem = trayIcon.toolsMenu.Append(
				wx.ID_ANY,
				_("Explain link in clipboard"),
				_("Send the link in the clipboard to Gemini and show the explanation"),
			)
			trayIcon.Bind(wx.EVT_MENU, self._onToolsMenu, self._toolsMenuItem)
		except Exception as error:
			log.debug(
				f"norlayLinkChecker: could not add the Tools menu item: {type(error).__name__}",
			)

	def _removeToolsMenuItem(self) -> None:
		item = self._toolsMenuItem
		if item is None:
			return
		self._toolsMenuItem = None
		trayIcon = None
		try:
			trayIcon = gui.mainFrame.sysTrayIcon
			trayIcon.Unbind(wx.EVT_MENU, self._onToolsMenu, item)
		except Exception as error:
			log.debug(
				f"norlayLinkChecker: could not unbind the Tools menu item: {type(error).__name__}",
			)
		try:
			if trayIcon is not None:
				trayIcon.toolsMenu.Remove(item)
			item.Destroy()
		except Exception as error:
			log.debug(
				f"norlayLinkChecker: could not remove the Tools menu item: {type(error).__name__}",
			)

	def terminate(self):
		self._pending += 1
		self._removeToolsMenuItem()
		self._unregisterSettingsPanel()
		close_report()
		super().terminate()

	def _onToolsMenu(self, event) -> None:
		self._checkClipboard(speakOnly=False)

	@script(
		description=_(
			"Sends the link in the clipboard to Gemini and shows the explanation "
			"in a read-only window",
		),
		gesture="kb:NVDA+control+shift+l",
	)
	def script_explainLinkInClipboard(self, gesture):
		self._checkClipboard(speakOnly=False)

	@script(
		description=_(
			"Speaks Gemini's explanation of the link in the clipboard",
		),
		gesture="kb:NVDA+alt+shift+l",
	)
	def script_speakLinkExplanation(self, gesture):
		self._checkClipboard(speakOnly=True)

	def _openSettings(self) -> None:
		try:
			gui.mainFrame.popupSettingsDialog(
				gui.settingsDialogs.NVDASettingsDialog,
				NorlaySettingsPanel,
			)
		except Exception as error:
			log.debug(
				f"norlayLinkChecker: could not open settings: {type(error).__name__}",
			)

	def _show_message(self, message: str, speakOnly: bool) -> None:
		"""Speak a short message, or show it in the read-only window."""
		if speakOnly:
			ui.message(message)
		else:
			show_report(_("Norlay Link Checker"), message)

	def _confirmSend(self) -> bool:
		dialog = wx.MessageDialog(
			gui.mainFrame,
			messages.consent_text(),
			_("Norlay Link Checker"),
			wx.YES_NO | wx.ICON_QUESTION,
		)
		try:
			dialog.SetYesNoLabels(_("Send"), _("Cancel"))
		except Exception:
			pass
		try:
			return dialog.ShowModal() == wx.ID_YES
		finally:
			dialog.Destroy()

	def _checkClipboard(self, speakOnly: bool) -> None:
		try:
			text = read_clipboard_text()
		except ClipboardHasFiles:
			self._show_message(_FILE_NOT_LINK, speakOnly)
			return
		except ClipboardHasNoText:
			self._show_message(_NO_TEXT, speakOnly)
			return
		except ClipboardUnavailable:
			ui.message(
				_("Another app is using the clipboard. Try again in a moment."),
			)
			return

		if not text.strip():
			ui.message(_("The clipboard is empty. Copy a link and try again."))
			return

		try:
			analysis = analyze(text)
		except NoURLFound:
			self._show_message(_NOT_A_LINK, speakOnly)
			return
		except InvalidURL as error:
			ui.message(_INVALID_MESSAGES.get(error.reason, _INVALID_MESSAGE_DEFAULT))
			return
		except URLTooLong:
			ui.message(
				_(
					"That link is longer than 8192 characters. Copy a shorter link and "
					"try again.",
				),
			)
			return
		except Exception as error:
			log.debug(f"norlayLinkChecker: check failed: {type(error).__name__}")
			ui.message(_("Something went wrong while checking the link."))
			return

		key = store.api_key()
		if not key:
			ui.message(messages.missing_key())
			self._openSettings()
			return

		if not store.consented():
			if not self._confirmSend():
				return
			store.set_consented(True)

		url = analysis.parsed.raw
		host = analysis.parsed.host or analysis.parsed.host_input or _("link")
		title = _("Norlay Link Checker — {host}").format(host=host)

		cached = _cache.get(url)
		if cached is not None:
			self._present(title, url, cached, speakOnly)
			return

		if not speakOnly:
			show_report(title, _("Checking with Gemini…"))

		self._pending += 1
		token = self._pending
		facts = _facts(analysis)
		send_url = url if store.include_query() else without_query(url)
		model = store.model()
		timeout = store.timeout()

		def work() -> str:
			return explain(send_url, facts, key, model, timeout=timeout)

		def success(answer: str) -> None:
			if token != self._pending:
				return
			_remember(url, answer)
			self._present(title, url, answer, speakOnly)

		def failure(error) -> None:
			if token != self._pending:
				return
			message = messages.describe(error)
			if speakOnly:
				ui.message(message)
			else:
				show_report(title, message)

		_run_in_background(work, success, failure)

	def _present(self, title: str, url: str, answer: str, speakOnly: bool) -> None:
		if speakOnly:
			ui.message(answer)
			return
		show_report(title, f"{url}\n\n{answer}\n\n{_DISCLAIMER}")
