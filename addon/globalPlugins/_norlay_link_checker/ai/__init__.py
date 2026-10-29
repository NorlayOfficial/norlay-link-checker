# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""AI support for the Norlay Link Checker.

Only Gemini is used.  Nothing in this package imports NVDA, so it can be
tested on its own.  The only module that touches the network is
:mod:`globalPlugins._norlay_link_checker.ai.gemini`.
"""

from __future__ import annotations

from .errors import GeminiError
from .gemini import DEFAULT_MODEL, MODEL_IDS, explain

__all__ = [
	"DEFAULT_MODEL",
	"MODEL_IDS",
	"GeminiError",
	"explain",
]
