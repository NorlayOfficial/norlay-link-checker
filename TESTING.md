# Manual test checklist

Run this on Windows 11 with NVDA 2026.1 and, if possible, 2026.3.
The add-on is `dist/norlayLinkChecker-1.1.4.nvda-addon`.

Everything here needs a real Gemini key and a live connection, so it cannot be
covered by the automated suite.

## 1. Install

- Open the `.nvda-addon` file, or use Add-on Store, Install from external
  source. NVDA should offer to install it.
- Say yes, restart NVDA.
- Add-on Store, Installed add-ons: version should be 1.1.4.
- NVDA menu, Tools should contain **Explain link in clipboard**.
- NVDA menu, Preferences, Settings should contain **Norlay Link Checker**.

## 2. Key setup

- Open the settings category with no key stored.
- Press OK with an empty key. Nothing should break.
- Press **Open the free key page**; your browser should open.
- Paste a wrong key and press **Test the key**. A dialog must appear saying
  "Google rejected the API key", with a working Close button.
- Paste the real key and press **Test the key**. A dialog must say "The key
  works.". Enter, Escape and the Close button must all dismiss it.
- Press OK, reopen Settings. The key field should still be filled, and the
  value must not be readable in `%APPDATA%\nvda\nvda.ini` (look for `dpapi:`).

## 3. Shortcut conflicts

- Open NVDA menu, Preferences, Input Gestures, expand **Norlay Link Checker**.
  Both commands should be listed, and neither should be marked as conflicting
  with an NVDA command.
- Turn on input help with `NVDA+1`, then press `NVDA+Control+Shift+L`. NVDA
  should read the add-on's description: "Sends the link in the clipboard to
  Gemini and shows the explanation in a read-only window". It must not say
  "Scroll rate", which is NVDA's own NVDA+Alt+L on a braille display.
- With a braille display connected, press `NVDA+Alt+L`. It should still change
  the braille automatic scroll rate, proving the add-on no longer claims it.
- Still in input help, press `NVDA+Alt+Shift+L`. It should read "Speaks
  Gemini's explanation of the link in the clipboard". Turn input help off again
  with `NVDA+1`.

## 4. Consent

- With the key set, copy `https://example.com/account` and press
  `NVDA+Control+Shift+L`.
- The first time, a dialog must name Google Gemini and
  generativelanguage.googleapis.com. Cancel: nothing should be sent and no
  window should appear.
- Press again and choose Send. After that, no dialog should appear again.

## 5. The window

- The explanation should appear in a window with a focused text field.
- NVDA should announce a read-only, multi-line edit.
- Type letters: nothing should change.
- Use arrows, Ctrl+Home, and read-all: all should work.
- Select a line and press Ctrl+C, then paste into Notepad: the text should
  appear. The add-on itself must not have changed the clipboard before that.
- Press Escape: the window should close but stay reusable, so the next check
  appears in the same window.
- Press the Close button: same result. Tab to it to confirm it is reachable by
  keyboard.
- Check that the window contains the address, the explanation, and the closing
  line "This explains the address. It is not a safety check."

## 6. Speech only

- Press `NVDA+Alt+Shift+L` on the same link.
- The answer should be spoken, with no window.
- Press it again immediately: the answer should come back at once, because the
  result was cached and no request was made.

## 7. Failure paths

- Disconnect the network and press the shortcut. Expect "I could not reach
  Google. Check that you are online."
- Set the model to a nonsense name in settings. Expect a message about the
  model, not a crash.
- If you have used the free allowance, expect a quota message with a wait time.

## 8. Privacy

- Copy `report.pdf`, then press `NVDA+Control+Shift+L`. The window must say
  **This is not a link**, and no request may be sent.
- Copy a real file in File Explorer (Ctrl+C), then press
  `NVDA+Control+Shift+L`. The window must say the clipboard holds a file, not
  a link. It must **not** say another app is using the clipboard.
- Copy a picture, for example with Snipping Tool. The add-on must say the
  clipboard holds something that is not text.
- Copy `nothing to see here` and press `NVDA+Alt+Shift+L`. The same sentence
  must be spoken, with no window.
- Open the NVDA log (`NVDA menu, Tools, View log`) and search for part of the
  address, and for the key. Neither should appear.
- Confirm `%APPDATA%\nvda\addons\norlayLinkChecker` contains no created files
  such as a cache or history.

## 9. Housekeeping

- Reload the add-on (NVDA menu, Tools, Reload plugins). The settings category
  must appear exactly once, not twice.
- Remove the add-on and restart NVDA. The Tools item and the settings category
  should be gone.
