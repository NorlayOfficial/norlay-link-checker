# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""A small result dialog with a real Close button.

Used by the settings panel so the outcome of "Test the key" is announced and
can be dismissed with Enter, Escape or the Close button, rather than only
appearing in a label that is easy to miss.
"""

from __future__ import annotations

import builtins

import wx

_ = builtins._  # noqa: F821


class ResultDialog(wx.Dialog):
	"""Show one short message in a read-only field with a Close button."""

	def __init__(self, parent, title: str, message: str) -> None:
		super().__init__(parent, wx.ID_ANY, title, style=wx.DEFAULT_DIALOG_STYLE)
		self.messageCtrl = wx.TextCtrl(
			self,
			wx.ID_ANY,
			value=message,
			style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH,
		)
		self.messageCtrl.SetMinSize((420, 90))
		self.closeButton = wx.Button(self, wx.ID_CLOSE, _("Close"))
		self.closeButton.SetDefault()
		self.closeButton.Bind(wx.EVT_BUTTON, self._on_close)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.messageCtrl, 1, wx.EXPAND | wx.ALL, 10)
		sizer.Add(self.closeButton, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
		self.SetSizer(sizer)

		# Enter and Escape both close the dialog, wherever the focus is.
		self.SetEscapeId(wx.ID_CLOSE)
		self.SetAffirmativeId(wx.ID_CLOSE)
		self.messageCtrl.SetFocus()

	def _on_close(self, event) -> None:
		self.EndModal(wx.ID_CLOSE)


def show_result(parent, title: str, message: str) -> None:
	"""Show *message* modally and wait for it to be dismissed."""
	dialog = ResultDialog(parent, title, message)
	try:
		dialog.ShowModal()
	finally:
		dialog.Destroy()
