# Security policy

## Reporting a problem

Please do not open a public issue for a security problem. Use GitHub's private
reporting instead: **Security → Report a vulnerability** on
<https://github.com/NorlayOfficial/norlay-link-checker/security/advisories/new>.

Include the add-on version, the NVDA version, what you expected and what
happened. Do not include a real API key or a link you would rather keep private.
Reports are acknowledged within a few days.

## What this add-on does with your data

This is the short version; the full text is in `README.md`.

- The clipboard is read only when you press a shortcut, and it is never written.
- A web address is sent only to Google's Gemini API, using a key you supply.
  Norlay has no server and never receives it.
- The address is never written to the NVDA log or to disk.
- The key is encrypted with Windows DPAPI and is never logged.
- Links are never opened, fetched or resolved by the add-on.

Anything that contradicts those statements is a security problem. Please report
it privately.

## Supported versions

Only the latest release receives fixes. Older versions can be updated from
[Releases](https://github.com/NorlayOfficial/norlay-link-checker/releases/latest).
