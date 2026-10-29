# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Read and write the add-on's settings through NVDA's configuration."""

from __future__ import annotations

import config

from globalPlugins._norlay_link_checker.ai import DEFAULT_MODEL

from .secrets import SecretsUnavailable, protect, unprotect

SECTION = "norlayLinkChecker"

SPEC = {
	"apiKey": "string(default='')",
	"model": f"string(default='{DEFAULT_MODEL}')",
	"timeout": "integer(default=25, min=5, max=120)",
	"includeQuery": "boolean(default=True)",
	"consented": "boolean(default=False)",
}


def register() -> None:
	"""Install the section in NVDA's configuration schema."""
	config.conf.spec[SECTION] = dict(SPEC)


def _section():
	return config.conf[SECTION]


def api_key() -> str:
	"""Return the decrypted key, or an empty string."""
	try:
		return unprotect(_section()["apiKey"])
	except Exception:
		return ""


def set_api_key(key: str) -> None:
	key = (key or "").strip()
	_section()["apiKey"] = protect(key) if key else ""


def has_api_key() -> bool:
	return bool(api_key())


def model() -> str:
	value = _section()["model"].strip()
	return value or DEFAULT_MODEL


def set_model(value: str) -> None:
	_section()["model"] = (value or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def timeout() -> int:
	return int(_section()["timeout"])


def set_timeout(value: int) -> None:
	_section()["timeout"] = max(5, min(120, int(value)))


def include_query() -> bool:
	return bool(_section()["includeQuery"])


def set_include_query(value: bool) -> None:
	_section()["includeQuery"] = bool(value)


def consented() -> bool:
	return bool(_section()["consented"])


def set_consented(value: bool) -> None:
	_section()["consented"] = bool(value)


__all__ = [
	"SPEC",
	"SecretsUnavailable",
	"api_key",
	"consented",
	"has_api_key",
	"include_query",
	"model",
	"register",
	"set_api_key",
	"set_consented",
	"set_include_query",
	"set_model",
	"set_timeout",
	"timeout",
]
