# Norlay Link Checker 1.1.4

The main shortcut no longer collides with a command built into NVDA.

* The explanation now opens with **NVDA+Control+Shift+L**. NVDA 2026.3 binds
  NVDA+Alt+L to "increase braille automatic scroll rate", so the add-on no
  longer claims that key.
* **NVDA+Alt+Shift+L** still speaks the explanation without opening a window.
  That combination was already free, and it is unchanged.
* Nothing else changed: the clipboard check, the privacy behaviour and the
  settings are exactly as they were in 1.1.3.

# Norlay Link Checker 1.1.3

The clipboard check now tells files, images, ordinary text and links apart
before anything is sent.

* Copying a file in File Explorer no longer produces the misleading "Another
  app is using the clipboard" message. The add-on says the clipboard holds a
  file, not a link.
* Copying a picture or another non-text format says the clipboard holds
  something that is not text.
* Ordinary text still says **This is not a link**, and a real web address is
  still checked normally.
* The clipboard is inspected with Windows' format list, so the add-on knows
  what it is looking at without opening or changing anything.

# Norlay Link Checker 1.1.2

Non-link clipboard text is now recognised before anything is sent.

* If the clipboard contains ordinary text, a file name such as `report.pdf`, or
  a dotted word such as `hello.there`, the add-on says **This is not a link**
  and sends nothing to Gemini.
* The check now uses the bundled Public Suffix List to decide whether bare text
  is a real web address, so `example.com` still works while `photo.jpg` does
  not.
* With the window shortcut the message appears in the read-only window; with
  the speech shortcut it is spoken.

# Norlay Link Checker 1.1.1

Smaller, easier-to-dismiss result windows.

* Test the key now opens a dialog that shows whether the key worked, with a
  Close button. Enter and Escape close it too.
* The explanation window has a Close button, and Escape closes it as before.
* The manifest description now mentions Google Gemini and the read-only
  window, instead of describing the old offline behaviour.

# Norlay Link Checker 1.1.0

The explanation now comes from Google Gemini, and it is shown in a read-only
text field instead of a browse-mode message.

* Add your own free Gemini API key in NVDA menu, Preferences, Settings,
  Norlay Link Checker. It is encrypted with Windows DPAPI before saving.
* `NVDA+Alt+L` opens the explanation in a read-only, navigable text window.
* `NVDA+Alt+Shift+L` speaks the explanation without opening a window.
* The default model is Gemini 3.5 Flash-Lite: free, fast, and light on quota.
* Quota is protected by short prompts, capped output, reduced thinking, and an
  in-memory cache of the last 32 answers.
* A one-time consent dialog names the provider and the exact host before the
  first address is sent.
* Model, timeout, and whether the query string is sent are configurable.

The local checks still run, but only to give Gemini accurate facts and to keep
the request small. The visible answer is Gemini's.

The add-on is no longer offline. Without a key or a connection it reports the
problem instead of showing a local report.

# Norlay Link Checker 1.0.1

Rebuilt with stricter packaging validation and a clean source tree. Behaviour is
unchanged from 1.0.0.

* The build now fails if a required file is missing, the manifest still has
  template placeholders, the manifest does not match `buildVars.py`, or editor
  and byte-code leftovers would be packed.
* The build also writes a byte-identical `.zip` for the manual install route,
  which does not depend on the Windows `.nvda-addon` file association.

# Norlay Link Checker 1.0.0

First release.

* Check the link in the clipboard with NVDA+Alt+L, or from NVDA menu, Tools,
  Check link in clipboard.
* Hear a one line summary with NVDA+Alt+Shift+L.
* See the protocol, the host, the controlling domain and the subdomain.
* Read warnings and notes about HTTP, IP addresses, misleading subdomains,
  punycode and mixed alphabets, invisible characters, unusual ports, long
  addresses and shortened links.
* Everything runs offline. The address is never sent, saved or opened.
