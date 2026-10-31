# Publishing to the NVDA Add-on Store

The store does not take uploads. A GitHub issue form creates a pull request in
[`nvaccess/addon-datastore`](https://github.com/nvaccess/addon-datastore), a bot
scans the file with VirusTotal and adds the metadata, and the pull request merges
once the automated checks pass. The first submission for an add-on also needs
manual approval from NV Access, which can take up to two weeks.

## Values for the form

Open <https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml>.

| Field | Value |
|---|---|
| Download URL | `https://github.com/NorlayOfficial/norlay-link-checker/releases/download/v<version>/norlayLinkChecker-<version>.nvda-addon` |
| Source URL | `https://github.com/NorlayOfficial/norlay-link-checker` |
| Publisher | `Norlay` |
| Channel | `stable` |
| License Name | `GPL v2` |
| License URL | `https://www.gnu.org/licenses/gpl-2.0.html` |

Use the **versioned** asset URL, never `/releases/latest/download/…`. The store
requires that a URL keep serving the same file for that version forever.

## Before submitting

1. `buildVars.py` has the new version, summary, description and changelog.
2. The test suite passes and `python3 build.py` produces the file.
3. `python3 tools/verify_archive.py` prints the size and SHA-256.
4. The tag matches the version and the release workflow has published both the
   versioned and the stable-name assets.
5. The page at <https://norlay.fit/norlay-link-checker/> shows the same version
   and SHA-256, and `downloads/norlay-link-checker.json` in the website matches.
6. `bun tools/norlay-link-checker-release-check.mjs --remote` passes in
   `services/website`.

## What the listing shows

The store reads the manifest inside the add-on, not this repository. The listing
therefore uses the manifest `summary`, `description`, `version`, `changelog` and
`doc/en/readme.html`. Changing any of them requires a new version and a new
submission; an existing submission cannot be edited.

## Immutability rules

- Never delete or replace a tag that has been submitted.
- Never replace a submitted release asset. GitHub release assets are pinned by
  their SHA-256 in the store.
- A mistake in the description or a typo in the changelog is fixed in the next
  version, not by editing the published one.

## Updates

After the first approval, each new version is the same form with the new
versioned URL. No further publisher approval is needed. Submit the version
before announcing it, and keep the release notes in `changelog.md` in step with
what the form will publish.

## Troubleshooting a failed pull request

The bot comments on the pull request with the exact validation error. The usual
causes are a URL that does not end in `.nvda-addon`, a version that is not
`major.minor.patch`, an NVDA API version that does not exist, a non-HTTPS URL in
the manifest, or a download that does not match the declared SHA-256. Fix the
release, then submit a new issue; do not edit the generated pull request.
