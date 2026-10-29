# Norlay Link Checker

A free NVDA add-on for Windows 11 that explains the link in your clipboard,
without opening it. Copy a link, press `NVDA+Alt+L`, and the explanation
appears in a read-only text window you can read, navigate and copy from.

This is the public release. Download the latest version from
[GitHub Releases](https://github.com/NorlayOfficial/norlay-link-checker/releases/latest)
or from [norlay.fit/norlay-link-checker](https://norlay.fit/norlay-link-checker/).

## How it works

The add-on sends the address to **Google Gemini**, which explains what the link
appears to be: the site it points to, what the path and query suggest, and
anything that deserves caution.

You use **your own free Gemini API key**. There is no subscription, no server
run by Norlay, and no payment of any kind.

## Requirements

- Windows 11 with NVDA 2026.1 or later.
- An internet connection when you check a link.
- A free Gemini API key from <https://aistudio.google.com/apikey>.

## Install

1. On Windows 11, make sure NVDA 2026.1 or later is running.
2. Download `norlayLinkChecker.nvda-addon` from
   [Releases](https://github.com/NorlayOfficial/norlay-link-checker/releases/latest).
3. Either open the downloaded file, or use NVDA menu, Tools, Add-on Store,
   **Install from external source** and pick it. Double-clicking depends on a
   working `.nvda-addon` file association; if Windows says it cannot access
   the file, use the Add-on Store route or the manual zip route in
   `INSTALL-WINDOWS.md`.
4. NVDA asks whether to install the add-on. Choose Yes.
5. Restart NVDA.

The release also includes a zip with the same contents, for people who install
by renaming it to `.nvda-addon` or by unpacking it.

## Set up the key once

1. Open NVDA menu, Preferences, Settings.
2. Choose **Norlay Link Checker** in the list of categories.
3. Paste your Gemini API key.
4. Optionally press **Test the key** to spend one request and confirm it
   works; the outcome appears in a small dialog with a Close button.
5. Press OK.

The key is encrypted with Windows DPAPI before NVDA saves its configuration,
so it is readable only by your Windows account. If it cannot be encrypted the
add-on refuses to store it rather than keeping it in plain text.

## Use

- Copy a link, then press `NVDA+Alt+L` to open the explanation in a read-only
  window. Press Escape or the Close button to hide it; the same window is
  reused next time.
- Press `NVDA+Alt+Shift+L` to hear the explanation without a window.
- Or use NVDA menu, Tools, Explain link in clipboard.
- Both shortcuts can be changed in NVDA's Input Gestures dialog, under
  Norlay Link Checker.
- If the clipboard holds ordinary text or a file name, the add-on says
  **This is not a link** and sends nothing.
- If the clipboard holds a file copied from File Explorer, it says the
  clipboard holds a file, not a link. Images and other non-text formats are
  reported the same way. None of these cases sends anything to Google.

Each answer ends with *This explains the address. It is not a safety check.*

## Choosing a model

The default is **Gemini 3.5 Flash-Lite**. It is free, fast, and handles this
narrow job well while using very little of the free allowance.

**Gemini 3.8 Flash** gives better answers but its free tier allows only a small
number of requests per day, so it runs out quickly. You can switch in settings
at any time.

Quota is protected in several ways:

- One short request per address, at most 320 output tokens.
- Thinking is reduced or off, since reasoning tokens count against the quota.
- The last 32 answers are remembered in memory, so checking the same link
  again costs nothing.
- No conversation history is resent, and no retries burn extra requests.
- The query string can be left out, which shortens the prompt.

## Privacy

- Nothing is sent until you press the shortcut, and the first time you are
  asked to confirm.
- The request goes only to `generativelanguage.googleapis.com`. Norlay has no
  server and never sees the address.
- Only the address and a few short facts already worked out locally are sent.
  The page itself is never fetched, opened or resolved.
- The address is never written to the NVDA log or to disk.
- Recent answers live in memory only, and disappear when NVDA exits.
- Your key is never logged and never shown in a report.
- The window is read-only: nothing in it can edit your clipboard.

The trade-off is explicit: this add-on is not offline. Without a key or a
connection it cannot produce an explanation.

## Limits

- Gemini only sees the address text. It cannot know what the page contains, so
  it can be wrong or overconfident.
- It is not a virus scanner and not a safety verdict. Keep your own judgement,
  especially before entering a password or payment details.
- Free tiers change. If the quota runs out, the add-on says so and suggests
  waiting.
- Model names change too; the model is selectable in settings for that reason.

## Build

Requires Python 3.13 (the version NVDA 2026.x runs). No third-party packages.

```
python3.13 build.py
```

The build writes two byte-identical files:

- `dist/norlayLinkChecker-<version>.nvda-addon`
- `dist/norlayLinkChecker-<version>.zip`

Builds are deterministic: the same sources produce a byte-identical archive.
The build validates the result before writing it and stops on a missing file,
a manifest placeholder, a manifest that disagrees with `buildVars.py`, a byte
order mark, or editor and byte-code leftovers.

Metadata lives in `buildVars.py` and `manifest.ini.tpl`. `build.py` is a small
dependency-free replacement for the official SCons template; the package
layout it produces is the one NVDA expects. See `BUILD.md` for the official
requirements and the checks that were made against NVDA's source. Before any
store submission, switch to the official `nvaccess/AddonTemplate` tooling for
translation extraction and SCons builds.

## Test

```
python3 -m unittest discover -s tests -t .
```

The suite covers the parser, the Public Suffix List, every local check, the
report wording, the Gemini payload and response parsing, error mapping, the
read-only window, consent, caching, a static privacy scan that allows network
code in exactly one file, a corpus, fuzz strings, and the NVDA adapter with
stubbed NVDA modules. No test touches the network.

## Layout

```
build.py                  builds the .nvda-addon and the .zip
buildVars.py              name, version, NVDA versions, changelog
manifest.ini.tpl          manifest template filled in by build.py
addon/
  doc/en/readme.html      help shown from the Add-on Store
  globalPlugins/
    norlayLinkChecker/    NVDA adapter: gestures, menu, window, settings
      __init__.py         the global plugin
      clipboard.py        reads the clipboard, never writes it
      reportWindow.py     the read-only text window
      resultDialog.py     a small Close-only dialog for the key test
      settings.py         the Gemini settings panel
      store.py            configuration access
      secrets.py          DPAPI encryption for the key
      messages.py         translatable failure sentences
    _norlay_link_checker/ pure Python, no NVDA imports
      parse.py            URL parsing and extraction
      psl.py              Public Suffix List lookup
      checks.py           the local checks
      analyzer.py         ties parsing and checks together
      report.py           plain-text report for the local checks
      ai/gemini.py        the only file that uses the network
      ai/prompt.py        the instruction sent to Gemini
      ai/sanitize.py      turns the reply into clean text
      ai/errors.py        typed failures, no user text
      data/               Public Suffix List, brands, shorteners
tests/                    unit, packaging and privacy tests
```

## Contributing

Bug reports and pull requests are welcome. See `CONTRIBUTING.md` for the build
and test commands and the house style, and `SECURITY.md` for reporting a
security issue privately.

## Licence

GPL v2 or later for the add-on. The bundled Public Suffix List is MPL 2.0, see
`LICENSE-PSL.txt`.
