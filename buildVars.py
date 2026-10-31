# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Add-on metadata used by build.py and by manifest.ini.tpl."""

addon_info = {
	"addon_name": "norlayLinkChecker",
	"addon_summary": "Norlay Link Checker",
	"addon_description": (
		"Explains the link in the clipboard without opening it. The address is "
		"sent to Google Gemini with your own free API key, and the answer opens "
		"in a read-only window you can read and copy. The page itself is never "
		"fetched, the address is never saved, and the link is never opened."
	),
	"addon_version": "1.1.4",
	"addon_author": "Norlay",
	"addon_url": "https://norlay.fit/norlay-link-checker/",
	"addon_sourceURL": "https://github.com/NorlayOfficial/norlay-link-checker",
	"addon_docFileName": "readme.html",
	"addon_minimumNVDAVersion": "2026.1",
	"addon_lastTestedNVDAVersion": "2026.3",
	"addon_updateChannel": None,
	"addon_license": "GPL v2",
	"addon_licenseURL": "https://www.gnu.org/licenses/gpl-2.0.html",
	"addon_changelog": (
		"1.1.4: the main shortcut is now NVDA+Control+Shift+L, because NVDA 2026.3 uses NVDA+Alt+L to increase the braille automatic scroll rate. NVDA+Alt+Shift+L still speaks the answer without a window. "
		"1.1.3: copied files and images are recognised as such instead of being "
		"reported as a busy clipboard. Links, ordinary text, files and other "
		"clipboard formats are told apart before anything is sent. 1.1.2: text "
		"that is not a link is recognised and reported instead of being sent to "
		"Gemini. File names and dotted words are no longer mistaken for web "
		"addresses. 1.1.1: the Test the key button now opens a dialog with the "
		"result and a Close button, and the explanation window has a Close "
		"button and closes with Escape. 1.1.0: the explanation comes from Google "
		"Gemini and is shown in a read-only text window. You add your own free "
		"Gemini API key once. Checks use one short request per address, remember "
		"recent answers, and never open the link."
	),
}
