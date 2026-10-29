# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""One reusable, read-only window for the explanation.

The layout follows NVDA's own log viewer: a frame holding a multiline text
control with ``wx.TE_READONLY``, focused as soon as it appears.  That is what
makes it navigable, selectable and copyable without being editable.

A Close button sits below the text so the window can be dismissed with Tab,
Enter or Escape, not only with the title bar button.
"""

from __future__ import annotations

import builtins

import gui
import wx

_ = builtins._  # noqa: F821

_window = None


class ReportWindow(wx.Frame):
	"""A frame showing text that the user can read but not change."""

	def __init__(self):
		super().__init__(
			gui.mainFrame,
			wx.ID_ANY,
			_("Norlay Link Checker"),
			style=wx.DEFAULT_FRAME_STYLE,
		)
		self.SetMinSize((560, 380))
		self.text = wx.TextCtrl(
			self,
			wx.ID_ANY,
			style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH,
		)
		font = self.text.GetFont()
		try:
			font.SetFaceName("Consolas")
		except Exception:
			pass
		self.text.SetFont(font)
		self.closeButton = wx.Button(self, wx.ID_CLOSE, _("Close"))
		self.closeButton.Bind(wx.EVT_BUTTON, self._on_close_button)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 8)
		sizer.Add(
			self.closeButton,
			0,
			wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM,
			8,
		)
		self.SetSizer(sizer)
		self.Bind(wx.EVT_CLOSE, self._on_close)
		self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

	def _on_close(self, event) -> None:
		# Keep the instance so the next check reuses this window.
		self.Hide()

	def _on_close_button(self, event) -> None:
		self.Hide()

	def _on_char_hook(self, event) -> None:
		if event.GetKeyCode() == wx.WXK_ESCAPE:
			self.Hide()
			return
		event.Skip()

	def show_content(self, title: str, text: str) -> None:
		self.SetTitle(title)
		self.text.SetValue(text)
		self.text.SetInsertionPoint(0)
		self.Show()
		self.Raise()
		self.text.SetFocus()


def show_report(title: str, text: str) -> None:
	"""Create the window if needed, fill it, and give it focus."""
	global _window
	if _window is None:
		_window = ReportWindow()
	_window.show_content(title, text)


def close_report() -> None:
	"""Destroy the window, used when the add-on is disabled or reloaded."""
	global _window
	window = _window
	_window = None
	if window is not None:
		try:
			window.Destroy()
		except Exception:
			pass
