# Building correctly

Notes from checking this add-on against NVDA's own source and the official
add-on tooling, so the package is not merely "a zip that looks right".

## What the official build looks like

The supported route is `nvaccess/AddonTemplate` with SCons:

- Python 3.13, 64-bit (NVDA 2026.3 declares `requires-python = ">=3.13,<3.14"`).
- SCons 4.10.1 or later.
- Optional: gettext for translations, Markdown for HTML documentation.
- `buildVars.py` holds the metadata, `manifest.ini.tpl` is filled in during the
  build, and the result is `addon-name-version.nvda-addon`.

This repo keeps the same layout and the same `buildVars.py` /
`manifest.ini.tpl` pairing, with a dependency-free `build.py` instead of SCons.
The manifest template is byte-for-byte the same shape as the official one,
including the `updateChannel = None` line.

## What NVDA actually requires

Checked in `nvaccess/nvda`, `source/addonHandler/__init__.py`:

- `manifest.ini` must sit at the archive root and load through
  `AddonManifest`, which validates `minimumNVDAVersion` and
  `lastTestedNVDAVersion` as API versions and requires
  `minimumNVDAVersion <= lastTestedNVDAVersion`.
- An add-on is compatible when its minimum version is not newer than the
  running NVDA and its last-tested version is not older than NVDA's
  `backCompatTo`. For NVDA 2026.3, `backCompatTo` is 2026.1, so
  `2026.1` / `2026.3` is exactly right.
- `updateChannel` is not in the manifest spec; NVDA ignores it, and the
  AddonTemplate still emits it. It is not a source of errors.
- Global plugins are discovered with `pkgutil.iter_modules`, and names starting
  with `_` are skipped. That is why the core lives in
  `globalPlugins/_norlay_link_checker` without being loaded as a plugin of its
  own.
- NVDA 2026.3 was released 2026-10-26, so `lastTestedNVDAVersion = 2026.3` is a
  released API version and does not force a beta/dev channel.

Addon Store rules (only relevant if this is ever submitted) add: `name` limited
to letters, numbers, underscores and hyphens; `version` as `major.minor` or
`major.minor.patch`; all URLs starting with `https://`. This add-on already
meets those.

## What `build.py` now enforces

The build stops with `BuildError` instead of producing a bad archive when:

- a required file is missing (`manifest.ini`, documentation, both plugin
  packages, the Public Suffix List data);
- `manifest.ini` starts with a byte order mark, which breaks `ConfigParser`
  on Windows;
- the manifest still contains `{...}` template placeholders;
- the manifest is not valid INI, has empty required fields, or its `name` /
  `version` disagree with `buildVars.py`;
- `minimumNVDAVersion` is newer than `lastTestedNVDAVersion`;
- `__pycache__`, `.pyc`, `.DS_Store`, `Thumbs.db` or `desktop.ini` would be
  packaged.

The privacy scan in `tests/test_privacy.py` allows network imports in exactly
one file, `ai/gemini.py`, and `ctypes` only in `norlayLinkChecker/secrets.py`,
which encrypts the key, and `norlayLinkChecker/clipboard.py`, which asks Windows
which formats the clipboard holds.

It writes both the `.nvda-addon` and a byte-identical `.zip`, and the zip is
what the manual Windows install uses, because that route never touches the
`.nvda-addon` file association.

## Problems found in this rebuild

1. **Byte-code could leak into the archive.** The exclusion filter matched
   files inside `__pycache__` but not the directory entry itself. Since the test
   suite imports the add-on and creates `__pycache__`, a build run after the
   tests could ship stale `.pyc` files from this machine. Fixed, with a
   regression test that plants a `.pyc` and checks the archive.
2. **Stray editor files were copied verbatim.** `.DS_Store` was present in the
   source folder. The build now filters it and validates that nothing slipped
   through.
3. **No validation of the result.** The old build wrote whatever it had.
   Required files, manifest contents and metadata agreement are now checked
   before the archive is written.
4. **Manifest was never parsed as INI.** A stray brace or a BOM would only have
   surfaced on the user's machine. Now it fails locally.
5. **Version string was duplicated** in tests, so a release bump could leave a
   stale assertion. Tests now read the version from `buildVars.py`.

Not a packaging problem: `Windows cannot access the specified device, path, or
file`. That message comes from Windows before NVDA sees the file, and it
followed the file from the OneDrive desktop to a flash drive. It is a broken
`.nvda-addon` association or security software, not the archive. See
`INSTALL-WINDOWS.md`.

## Reproduce the checks

```
python3.13 build.py
python3.13 -m unittest discover -s tests -t .
unzip -l dist/norlayLinkChecker-1.1.3.nvda-addon
```

To confirm the sources are valid for NVDA's Python rather than only for the
local interpreter:

```
python3.14 - <<'PY'
import ast, pathlib
for p in pathlib.Path("addon").rglob("*.py"):
    ast.parse(p.read_text(encoding="utf-8"), filename=str(p), feature_version=(3, 13))
print("3.13 syntax OK")
PY
```

## Before any future submission

Switch to `nvaccess/AddonTemplate` so translations, `manifest-translated.ini`
and SCons packaging are handled by the official tooling, and drop this
`build.py`. Nothing here has been published, uploaded or submitted.
