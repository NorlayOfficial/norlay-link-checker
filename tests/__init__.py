"""Make the add-on's pure-Python package importable in tests."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_ROOT = os.path.join(PROJECT_ROOT, "addon", "globalPlugins")
if PLUGINS_ROOT not in sys.path:
	sys.path.insert(0, PLUGINS_ROOT)
