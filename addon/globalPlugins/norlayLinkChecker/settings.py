# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""The Gemini settings panel, shown in NVDA's normal Settings dialog."""

from __future__ import annotations

import builtins
import threading
import webbrowser

import gui
import wx

from globalPlugins._norlay_link_checker.ai import DEFAULT_MODEL, MODEL_IDS, GeminiError, explain

from . import messages, store
from .resultDialog import show_result
from .secrets import SecretsUnavailable, protect

_ = builtins._  # noqa: F821

KEY_PAGE = "https://aistudio.google.com/apikey"

_MODEL_LABELS = {
	"gemini-3.5-flash-lite": _(
		"Gemini 3.5 Flash-Lite. Recommended: free, fast and light on quota.",
	),
	"gemini-3.8-flash": _(
		"Gemini 3.8 Flash. Best answers, but the free daily limit is small.",
	),
	"gemini-3.6-flash": _("Gemini 3.6 Flash. Previous generation."),
}


def _label_for(model_id: str) -> str:
	return _MODEL_LABELS.get(model_id, model_id)


class NorlaySettingsPanel(gui.settingsDialogs.SettingsPanel):
	"""Choose the key and how much is spent per check."""

	title = _("Norlay Link Checker")

	def makeSettings(self, settingsSizer) -> None:
		description = wx.StaticText(
			self,
			label=_(
				"Each check sends the address to Google Gemini and shows the "
				"answer in a read-only window. A free API key is required.",
			),
		)
		description.Wrap(520)
		settingsSizer.Add(description, 0, wx.ALL, 4)

		settingsSizer.Add(
			wx.StaticText(self, label=_("Gemini API key")),
			0,
			wx.TOP | wx.LEFT | wx.RIGHT,
			6,
		)
		self.keyCtrl = wx.TextCtrl(
			self,
			value=store.api_key(),
			style=wx.TE_PASSWORD,
		)
		self.keyCtrl.SetName(_("Gemini API key"))
		settingsSizer.Add(self.keyCtrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

		self.keyPageButton = wx.Button(self, label=_("Open the free key page"))
		self.keyPageButton.Bind(wx.EVT_BUTTON, self._on_open_key_page)
		settingsSizer.Add(self.keyPageButton, 0, wx.ALL, 6)

		settingsSizer.Add(
			wx.StaticText(self, label=_("Model")),
			0,
			wx.TOP | wx.LEFT | wx.RIGHT,
			6,
		)
		self.modelIds = list(MODEL_IDS)
		current = store.model()
		if current not in self.modelIds:
			self.modelIds.append(current)
		self.modelCtrl = wx.Choice(
			self,
			choices=[_label_for(model_id) for model_id in self.modelIds],
		)
		self.modelCtrl.SetName(_("Model"))
		self.modelCtrl.SetSelection(self.modelIds.index(current))
		settingsSizer.Add(self.modelCtrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

		settingsSizer.Add(
			wx.StaticText(self, label=_("Seconds to wait for an answer")),
			0,
			wx.TOP | wx.LEFT | wx.RIGHT,
			6,
		)
		self.timeoutCtrl = wx.SpinCtrl(
			self,
			min=5,
			max=120,
			initial=store.timeout(),
		)
		self.timeoutCtrl.SetName(_("Seconds to wait for an answer"))
		settingsSizer.Add(self.timeoutCtrl, 0, wx.LEFT | wx.RIGHT, 6)

		self.includeQueryCtrl = wx.CheckBox(
			self,
			label=_("Send the query string, the part after the question mark"),
		)
		self.includeQueryCtrl.SetValue(store.include_query())
		settingsSizer.Add(self.includeQueryCtrl, 0, wx.ALL, 6)

		self.testButton = wx.Button(self, label=_("Test the key"))
		self.testButton.Bind(wx.EVT_BUTTON, self._on_test)
		settingsSizer.Add(self.testButton, 0, wx.ALL, 6)

		self.statusCtrl = wx.StaticText(self, label="")
		settingsSizer.Add(self.statusCtrl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

	def _selected_model(self) -> str:
		index = self.modelCtrl.GetSelection()
		if index < 0 or index >= len(self.modelIds):
			return DEFAULT_MODEL
		return self.modelIds[index]

	def _on_open_key_page(self, event) -> None:
		try:
			webbrowser.open(KEY_PAGE)
		except Exception:
			self.statusCtrl.SetLabel(KEY_PAGE)

	def _on_test(self, event) -> None:
		key = self.keyCtrl.GetValue().strip()
		if not key:
			self.statusCtrl.SetLabel(messages.missing_key())
			return
		model = self._selected_model()
		timeout = self.timeoutCtrl.GetValue()
		self.testButton.Disable()
		self.statusCtrl.SetLabel(_("Sending one test request to Google…"))

		def work():
			try:
				explain(
					"https://example.com/account",
					["scheme=https"],
					key,
					model,
					timeout=min(20, timeout),
				)
			except GeminiError as error:
				return error
			except Exception:
				return GeminiError("response")
			return None

		def report(result):
			self.testButton.Enable()
			self.statusCtrl.SetLabel("")
			if result is None:
				show_result(
					self,
					_("Norlay Link Checker"),
					_("The key works."),
				)
			else:
				show_result(
					self,
					_("Norlay Link Checker"),
					messages.describe(result),
				)

		threading.Thread(
			target=lambda: wx.CallAfter(report, work()),
			daemon=True,
		).start()

	def isValid(self) -> bool:
		key = self.keyCtrl.GetValue().strip()
		if key:
			try:
				protect(key)
			except SecretsUnavailable:
				gui.messageBox(
					_(
						"The key could not be encrypted, so it was not saved. "
						"The add-on will not store it in plain text.",
					),
					_("Norlay Link Checker"),
					wx.OK | wx.ICON_ERROR,
					self,
				)
				return False
		return True

	def onSave(self) -> None:
		key = self.keyCtrl.GetValue().strip()
		previous = store.api_key()
		store.set_model(self._selected_model())
		store.set_timeout(self.timeoutCtrl.GetValue())
		store.set_include_query(self.includeQueryCtrl.GetValue())
		try:
			store.set_api_key(key)
		except SecretsUnavailable:
			return
		if key != previous:
			# A new key means a new consent prompt before the first send.
			store.set_consented(False)
