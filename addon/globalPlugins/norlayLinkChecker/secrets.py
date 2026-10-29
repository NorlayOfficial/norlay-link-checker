# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Protect the Gemini API key at rest.

NVDA keeps configuration in a plain text INI file.  A key is therefore
encrypted with the Windows Data Protection API before it is written, which
binds it to the current Windows account.  If that is not possible the key is
not saved at all, rather than being written in the clear.
"""

from __future__ import annotations

import base64
import ctypes
import sys
from ctypes import wintypes

_PREFIX = "dpapi:"


class SecretsUnavailable(Exception):
	"""The key could not be encrypted on this system."""


class _DataBlob(ctypes.Structure):
	_fields_ = [
		("cbData", wintypes.DWORD),
		("pbData", ctypes.POINTER(ctypes.c_char)),
	]


def available() -> bool:
	return sys.platform == "win32"


def _crypt32():
	if not available():
		raise SecretsUnavailable("DPAPI is only available on Windows")
	try:
		return ctypes.WinDLL("crypt32", use_last_error=True)
	except OSError as error:
		raise SecretsUnavailable("crypt32 could not be loaded") from error


def _kernel32():
	try:
		return ctypes.WinDLL("kernel32", use_last_error=True)
	except OSError as error:
		raise SecretsUnavailable("kernel32 could not be loaded") from error


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
	buffer = ctypes.create_string_buffer(data, len(data))
	blob = _DataBlob(
		len(data),
		ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)),
	)
	return blob, buffer


def protect(text: str) -> str:
	"""Return an opaque, encrypted string for *text*."""
	if not text:
		return ""
	crypt32 = _crypt32()
	plain = text.encode("utf-8")
	in_blob, _keep = _blob(plain)
	out_blob = _DataBlob()
	ok = crypt32.CryptProtectData(
		ctypes.byref(in_blob),
		None,
		None,
		None,
		None,
		0,
		ctypes.byref(out_blob),
	)
	if not ok:
		raise SecretsUnavailable(f"CryptProtectData failed ({ctypes.get_last_error()})")
	try:
		raw = ctypes.string_at(out_blob.pbData, out_blob.cbData)
	finally:
		_kernel32().LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))
	return _PREFIX + base64.b64encode(raw).decode("ascii")


def unprotect(value: str) -> str:
	"""Return the key from a stored value, or an empty string on failure."""
	if not value or not value.startswith(_PREFIX):
		return ""
	crypt32 = _crypt32()
	try:
		raw = base64.b64decode(value[len(_PREFIX) :], validate=True)
	except (ValueError, TypeError):
		return ""
	in_blob, _keep = _blob(raw)
	out_blob = _DataBlob()
	ok = crypt32.CryptUnprotectData(
		ctypes.byref(in_blob),
		None,
		None,
		None,
		None,
		0,
		ctypes.byref(out_blob),
	)
	if not ok:
		return ""
	try:
		plain = ctypes.string_at(out_blob.pbData, out_blob.cbData)
	finally:
		_kernel32().LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))
	return plain.decode("utf-8", "replace")
