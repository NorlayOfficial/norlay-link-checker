"""Pytest configuration.

The unittest suite works without pytest; this file only makes the package
importable when the tests are run with pytest.
"""

import os
import sys

PLUGINS_ROOT = os.path.join(
	os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
	"addon",
	"globalPlugins",
)
if PLUGINS_ROOT not in sys.path:
	sys.path.insert(0, PLUGINS_ROOT)
