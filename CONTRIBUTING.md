# Contributing

Thanks for helping. This add-on explains a link from the clipboard, and it is
deliberately small: one request, one answer, nothing stored. Changes that make
it do more than that need a very good reason.

## Before you start

- Open an issue for anything larger than a typo or a small fix, so the design can
  be agreed before code is written.
- Read `SECURITY.md` if your report is a security problem. Do not open a public
  issue for it.

## Build and test

You need Python 3.11 or later; the tests use only the standard library.

```
python3 -m unittest discover -s tests -t .
python3 build.py
```

`build.py` is dependency free and produces two byte-identical files in `dist/`.
It validates the staged add-on before writing anything, so a failing build is a
real failure, not a packaging quirk.

The test suite stubs NVDA and wxPython, so it runs on macOS and Linux as well as
Windows. No test may touch the network.

## House style

- Tabs for indentation, as in the existing files.
- Plain, calm sentences in user-facing text. Say what happened and what to do
  next; do not blame the user.
- Every user-facing string goes through `_()` so it can be translated.
- Network access belongs in `_norlay_link_checker/ai/gemini.py` and nowhere
  else. `tests/test_privacy.py` enforces that.
- `ctypes` is allowed only in `secrets.py` (DPAPI) and `clipboard.py` (clipboard
  formats). The same test enforces it.
- Never add logging of a URL, a key, or clipboard content.

## Pull requests

1. Keep the change focused, and say what you tested.
2. Run the suite and the build before pushing.
3. If you changed behaviour, update `changelog.md`, `README.md` and the help page
   in `addon/doc/en/readme.html`.
4. Version numbers and release notes are set in `buildVars.py`; a maintainer
   bumps them at release time.

By contributing you agree that your work is licensed under GPL v2 or later, the
same licence as the rest of the add-on.
