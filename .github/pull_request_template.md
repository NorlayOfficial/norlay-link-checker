## What this changes

<!-- One or two sentences. Say what was wrong or missing, not just what the diff does. -->

## Why

<!-- The problem a user had. A link to an issue if there is one. -->

## Testing

<!-- What you ran, and on what. "python3 -m unittest discover -s tests -t ." and "python3 build.py" are the minimum. -->

- [ ] Tests pass (`python3 -m unittest discover -s tests -t .`)
- [ ] The add-on builds (`python3 build.py`)
- [ ] The archive checks out (`python3 tools/verify_archive.py`)

## Checklist

- [ ] User-facing text is wrapped in `_()` and stays calm and plain
- [ ] No URL, key or clipboard content is logged or written to disk
- [ ] Network access is still confined to `_norlay_link_checker/ai/gemini.py`
- [ ] `changelog.md` updated if behaviour changed
- [ ] `README.md` and `addon/doc/en/readme.html` updated if behaviour changed
