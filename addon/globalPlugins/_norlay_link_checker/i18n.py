# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Translation hook for the pure-Python core.

The core package has to stay importable outside NVDA so that it can be unit
tested on any machine.  All user facing strings therefore call ``_`` from this
module.  At start up the NVDA adapter replaces the identity function with
NVDA's own gettext function.
"""

from __future__ import annotations

from collections.abc import Callable

_translator: Callable[[str], str]


def _identity(message: str) -> str:
	return message


_translator = _identity


def _(message: str) -> str:
	"""Return *message* translated, or unchanged when no translator is set."""
	return _translator(message)


def set_translator(translator: Callable[[str], str]) -> None:
	"""Install the translation function used by the core package."""
	global _translator
	_translator = translator
