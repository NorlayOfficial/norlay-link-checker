"""Default gestures must not collide with commands NVDA already owns.

The Add-on Store review caught the add-on claiming NVDA+Alt+L, which NVDA
2026.3 binds to "increase braille automatic scroll rate"
(``source/globalCommands.py``, ``script_increaseBrailleAutoScrollRate``). An
add-on gesture on top of an NVDA command wins or loses depending on load order,
which produces a bug that is hard to reproduce and impossible to explain to a
user, so the add-on must not claim one at all.

The defaults below are the ones an add-on that reads the clipboard might be
tempted to use. They are taken from the NVDA 2026.3 user guide and checked
against the NVDA source tree; this list only needs extending if it gains a
default that somebody might want to reuse.
"""

import os
import re
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(
	PROJECT_ROOT,
	"addon",
	"globalPlugins",
	"norlayLinkChecker",
	"__init__.py",
)
README = os.path.join(PROJECT_ROOT, "README.md")
HELP = os.path.join(PROJECT_ROOT, "addon", "doc", "en", "readme.html")

#: NVDA 2026.3 defaults that overlap the letters an add-on like this would use.
NVDA_DEFAULTS = frozenset({
	"kb:nvda+l",  # read current line
	"kb:nvda+alt+t",  # braille: cycle braille mode
	"kb:nvda+alt+j",  # braille: decrease automatic scroll rate
	"kb:nvda+alt+k",  # braille: toggle automatic scroll
	"kb:nvda+alt+l",  # braille: increase automatic scroll rate
	"kb:nvda+shift+l",  # magnifier: show entire screen overview
})

#: What the add-on should register, and why.
EXPECTED = {
	"kb:nvda+control+shift+l": "opens the explanation in a window",
	"kb:nvda+alt+shift+l": "speaks the explanation without a window",
}

PRIMARY_HUMAN = "NVDA+Control+Shift+L"
OLD_HUMAN = "NVDA+Alt+L"


def gestures():
	with open(PLUGIN, encoding="utf-8") as handle:
		text = handle.read()
	return re.findall(r'gesture="(kb:[^"]+)"', text)


class GestureTests(unittest.TestCase):
	def test_no_gesture_shadows_an_nvda_default(self):
		for gesture in gestures():
			with self.subTest(gesture=gesture):
				self.assertNotIn(
					gesture.lower(),
					NVDA_DEFAULTS,
					f"{gesture} is already bound by NVDA",
				)

	def test_the_expected_gestures_are_registered(self):
		self.assertEqual({gesture.lower() for gesture in gestures()}, set(EXPECTED))

	def test_gestures_use_the_nvda_modifier(self):
		# A gesture without NVDA is global: it would fire inside every
		# application and take the key away from the user's own shortcuts.
		for gesture in gestures():
			with self.subTest(gesture=gesture):
				self.assertTrue(gesture.lower().startswith("kb:nvda+"))

	def test_the_documented_shortcut_matches_the_registered_one(self):
		with open(README, encoding="utf-8") as handle:
			readme = handle.read()
		with open(HELP, encoding="utf-8") as handle:
			help_page = handle.read()
		self.assertIn(PRIMARY_HUMAN, readme)
		self.assertIn(PRIMARY_HUMAN, help_page)
		self.assertNotIn(OLD_HUMAN, readme)
		self.assertNotIn(OLD_HUMAN, help_page)


if __name__ == "__main__":
	unittest.main()
