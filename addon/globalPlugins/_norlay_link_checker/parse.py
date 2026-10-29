# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Find a link in text and split it into its parts.

The parser is deliberately forgiving.  It never resolves, opens or fetches
anything; it only looks at the characters the user copied.
"""

from __future__ import annotations

import ipaddress
import re

from . import psl
from .model import HostInfo, ParsedURL

#: The longest input that is examined.  Longer clipboard text is truncated by
#: the caller so that the check always finishes quickly.
MAX_URL_CHARS = 8192

WEB_SCHEMES = frozenset({"http", "https", "ftp", "ftps", "ws", "wss"})
LOCAL_SCHEMES = frozenset({"file"})
SCRIPT_SCHEMES = frozenset({"javascript", "vbscript"})
DATA_SCHEMES = frozenset({"data"})
EMAIL_SCHEMES = frozenset({"mailto"})
PHONE_SCHEMES = frozenset({"tel", "sms"})
OTHER_SCHEMES = frozenset({"about", "blob", "chrome", "magnet", "irc", "news"})

_KNOWN_SCHEMES = (
	WEB_SCHEMES
	| LOCAL_SCHEMES
	| SCRIPT_SCHEMES
	| DATA_SCHEMES
	| EMAIL_SCHEMES
	| PHONE_SCHEMES
	| OTHER_SCHEMES
)

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")

_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):", re.ASCII)

_SCHEME_URL_RE = re.compile(
	r"(?i)\b(?:https?|ftps?|wss?|file|chrome)://[^\s<>\"'`]+",
)
_OPAQUE_URL_RE = re.compile(
	r"(?i)\b(?:javascript|vbscript|data|mailto|tel|sms|about|blob):[^\s<>\"'`]*",
)

_TOKEN_RE = re.compile(r"\S+")

_BARE_HOST_RE = re.compile(
	r"^(?P<host>\[[0-9A-Fa-f:.]+\]|(?:[^\s/?#@:\[\]]+\.)+[^\s/?#@:\[\].]+)"
	r"(?::(?P<port>[0-9]{1,5}))?"
	r"(?P<tail>[/?#].*)?$",
	re.DOTALL,
)

_TRAILING_PUNCTUATION = ".,;:!?'\"\u00bb\u201d\u2019"
_OPENERS = {"(": ")", "[": "]", "{": "}", "<": ">"}
_CLOSERS = {closer: opener for opener, closer in _OPENERS.items()}


class LinkCheckerError(Exception):
	"""Base class for problems that can be explained to the user."""

	def __init__(self, reason: str = ""):
		super().__init__(reason)
		self.reason = reason


class NoURLFound(LinkCheckerError):
	"""No link could be found in the text."""


class InvalidURL(LinkCheckerError):
	"""A link was found but its structure cannot be read."""


class URLTooLong(LinkCheckerError):
	"""The link is longer than the supported maximum."""


def _trim(token: str) -> str:
	"""Remove punctuation that wraps a copied token, keeping balanced pairs."""
	result = token
	while result and result[0] in "\"'([{<":
		result = result[1:]
	while result:
		last = result[-1]
		if last in _TRAILING_PUNCTUATION:
			result = result[:-1]
			continue
		opener = _CLOSERS.get(last)
		if opener is not None and result.count(last) > result.count(opener):
			result = result[:-1]
			continue
		break
	return result


def _plausible_last_label(label: str) -> bool:
	if len(label) < 2:
		return False
	if label.isdigit():
		return False
	return any(character.isalpha() for character in label)


def _looks_like_bare_host(token: str) -> bool:
	match = _BARE_HOST_RE.match(token)
	if not match:
		return False
	host = match.group("host")
	if host.startswith("["):
		return True
	labels = host.split(".")
	if not _plausible_last_label(labels[-1]):
		return False
	# Check the last labels against the bundled Public Suffix List, so that
	# "report.pdf" and "hello.there" are not treated as web addresses.  The
	# list stores some international suffixes in their Unicode form and others
	# in punycode, so both forms are tried.
	return psl.has_known_suffix(host) or psl.has_known_suffix(encode_host(host))


def _span_contains(outer: tuple[int, int], inner: tuple[int, int]) -> bool:
	return outer[0] <= inner[0] and inner[1] <= outer[1]


def extract_urls(text: str) -> list[str]:
	"""Return every link found in *text*, in the order they appear.

	Links with an explicit scheme are found first, then bare host names in the
	remaining text.  Duplicates are removed.
	"""
	spans: list[tuple[int, int]] = []
	for pattern in (_SCHEME_URL_RE, _OPAQUE_URL_RE):
		for match in pattern.finditer(text):
			candidate = (match.start(), match.end())
			if candidate[1] <= candidate[0]:
				continue
			spans.append(candidate)
	spans.sort(key=lambda span: (span[0], -(span[1] - span[0])))

	accepted: list[tuple[int, int]] = []
	for span in spans:
		if any(_span_contains(existing, span) for existing in accepted):
			continue
		accepted.append(span)

	positioned: list[tuple[int, str]] = []
	for start, end in accepted:
		url = _trim(text[start:end])
		if url:
			positioned.append((start, url))

	masked = list(text)
	for start, end in accepted:
		for index in range(start, end):
			masked[index] = " "
	remainder = "".join(masked)

	bare: list[tuple[int, str]] = []
	for match in _TOKEN_RE.finditer(remainder):
		token = _trim(match.group(0))
		if token and _looks_like_bare_host(token):
			bare.append((match.start(), token))

	combined = list(positioned)
	combined.extend(bare)
	combined.sort(key=lambda item: item[0])

	unique: list[str] = []
	seen: set[str] = set()
	for _, url in combined:
		key = url.lower()
		if key in seen:
			continue
		seen.add(key)
		unique.append(url)
	return unique


def _percent_decode(text: str) -> str:
	pieces: list[str] = []
	index = 0
	while index < len(text):
		character = text[index]
		if (
			character == "%"
			and index + 2 < len(text)
			and text[index + 1] in _HEX_DIGITS
			and text[index + 2] in _HEX_DIGITS
		):
			pieces.append(chr(int(text[index + 1 : index + 3], 16)))
			index += 3
			continue
		pieces.append(character)
		index += 1
	return "".join(pieces)


def _decode_punycode_label(label: str) -> str:
	try:
		return label.encode("ascii").decode("idna")
	except (UnicodeError, ValueError):
		pass
	try:
		return label[4:].encode("ascii").decode("punycode")
	except (UnicodeError, ValueError):
		return label


def decode_host(host: str) -> str:
	"""Turn ``xn--`` labels into their Unicode form for display."""
	labels = []
	for label in host.split("."):
		if label.lower().startswith("xn--"):
			labels.append(_decode_punycode_label(label))
		else:
			labels.append(label)
	return ".".join(labels)


def encode_host(host: str) -> str:
	"""Turn a Unicode host into its ASCII (punycode) form."""
	try:
		return host.encode("idna").decode("ascii")
	except (UnicodeError, ValueError):
		pass
	labels = []
	for label in host.split("."):
		try:
			labels.append(label.encode("idna").decode("ascii"))
		except (UnicodeError, ValueError):
			labels.append(label)
	return ".".join(labels)


def _split_authority(remainder: str) -> tuple[str, str]:
	"""Split the authority from the path, query and fragment.

	Backslashes are treated as separators because browsers do the same.
	"""
	for index, character in enumerate(remainder):
		if character in "/?#\\":
			return remainder[:index], remainder[index:]
	return remainder, ""


def _split_tail(tail: str) -> tuple[str, str | None, str | None]:
	fragment = None
	query = None
	if "#" in tail:
		tail, fragment = tail.split("#", 1)
	if "?" in tail:
		tail, query = tail.split("?", 1)
	return tail, query, fragment


def _parse_host_and_port(
	hostport: str,
) -> tuple[str, str | None, int | None, str | None]:
	"""Return host as written, port text, port number and port error."""
	port_text: str | None = None
	if hostport.startswith("["):
		close = hostport.find("]")
		if close < 0:
			raise InvalidURL("ipv6_brackets")
		host = hostport[1:close]
		after = hostport[close + 1 :]
		if after:
			if not after.startswith(":"):
				raise InvalidURL("ipv6_trailing")
			port_text = after[1:]
	elif hostport.count(":") > 1:
		raise InvalidURL("ipv6_brackets")
	elif ":" in hostport:
		host, _, port_text = hostport.rpartition(":")
	else:
		host = hostport

	if not host:
		raise InvalidURL("no_host")

	port: int | None = None
	port_error: str | None = None
	if port_text is not None:
		if not port_text:
			port_error = "empty"
		elif not port_text.isascii() or not port_text.isdigit():
			port_error = "not_a_number"
		else:
			value = int(port_text)
			if value > 65535:
				port_error = "out_of_range"
			else:
				port = value
	return host, port_text, port, port_error


def _kind_for_scheme(scheme: str | None) -> str:
	if scheme is None:
		return "web"
	if scheme in WEB_SCHEMES:
		return "web"
	if scheme in LOCAL_SCHEMES:
		return "local"
	if scheme in SCRIPT_SCHEMES:
		return "script"
	if scheme in DATA_SCHEMES:
		return "data"
	if scheme in EMAIL_SCHEMES:
		return "email"
	if scheme in PHONE_SCHEMES:
		return "phone"
	return "other"


def _opaque_url(raw: str, scheme: str, remainder: str) -> ParsedURL:
	kind = _kind_for_scheme(scheme)
	path, query, fragment = _split_tail(remainder)
	return ParsedURL(
		raw=raw,
		scheme=scheme,
		kind=kind,
		host="",
		host_ascii="",
		host_input="",
		port=None,
		port_text=None,
		port_error=None,
		userinfo=None,
		path=path,
		query=query,
		fragment=fragment,
		trailing_dot=False,
		percent_encoded_host=False,
		is_ip=False,
		ip_version=None,
	)


def parse_url(raw: str) -> ParsedURL:
	"""Parse *raw* into a :class:`ParsedURL`.

	Raises :class:`InvalidURL` when there is no usable host at all, and
	:class:`URLTooLong` when the string exceeds :data:`MAX_URL_CHARS`.
	"""
	text = raw.strip()
	if not text:
		raise InvalidURL("empty")
	if len(text) > MAX_URL_CHARS:
		raise URLTooLong("too_long")

	scheme: str | None = None
	remainder = text
	match = _SCHEME_RE.match(text)
	if match:
		candidate = match.group(1).lower()
		after = text[match.end() :]
		if after.startswith("//") or candidate in _KNOWN_SCHEMES:
			scheme = candidate
			remainder = after

	kind = _kind_for_scheme(scheme)
	if kind not in ("web", "local"):
		return _opaque_url(text, scheme or "", remainder)

	if remainder.startswith("//"):
		remainder = remainder[2:]
	authority, tail = _split_authority(remainder)

	if not authority:
		if kind == "local":
			path, query, fragment = _split_tail(tail)
			return ParsedURL(
				raw=text,
				scheme=scheme,
				kind=kind,
				host="",
				host_ascii="",
				host_input="",
				port=None,
				port_text=None,
				port_error=None,
				userinfo=None,
				path=path,
				query=query,
				fragment=fragment,
				trailing_dot=False,
				percent_encoded_host=False,
				is_ip=False,
				ip_version=None,
			)
		raise InvalidURL("no_host")

	userinfo: str | None = None
	hostport = authority
	at_sign = authority.rfind("@")
	if at_sign >= 0:
		userinfo = authority[:at_sign]
		hostport = authority[at_sign + 1 :]
		if not hostport:
			raise InvalidURL("no_host")

	host_input, port_text, port, port_error = _parse_host_and_port(hostport)

	percent_encoded_host = "%" in host_input
	host_work = host_input
	if percent_encoded_host:
		decoded = _percent_decode(host_input)
		if not any(character in decoded for character in "/\\@?#"):
			host_work = decoded

	trailing_dot = host_work.endswith(".")
	if trailing_dot:
		host_work = host_work[:-1]
	if not host_work:
		raise InvalidURL("no_host")

	host_work = host_work.lower()
	host_display = decode_host(host_work)
	host_ascii = encode_host(host_display)

	is_ip = False
	ip_version: int | None = None
	ip_candidate = host_work.split("%", 1)[0]
	try:
		address = ipaddress.ip_address(ip_candidate)
	except ValueError:
		pass
	else:
		is_ip = True
		ip_version = address.version

	path, query, fragment = _split_tail(tail)
	return ParsedURL(
		raw=text,
		scheme=scheme,
		kind=kind,
		host=host_display,
		host_ascii=host_ascii,
		host_input=host_input,
		port=port,
		port_text=port_text,
		port_error=port_error,
		userinfo=userinfo,
		path=path,
		query=query,
		fragment=fragment,
		trailing_dot=trailing_dot,
		percent_encoded_host=percent_encoded_host,
		is_ip=is_ip,
		ip_version=ip_version,
	)


def _numeric_label_value(label: str) -> int | None:
	lowered = label.lower()
	if not lowered:
		return None
	try:
		if lowered.startswith("0x"):
			digits = lowered[2:]
			if not digits or any(character not in _HEX_DIGITS for character in digits):
				return None
			return int(digits, 16)
		if (
			len(lowered) > 1
			and lowered.startswith("0")
			and lowered.isascii()
			and lowered[1:].isdigit()
		):
			return int(lowered[1:], 8)
		if lowered.isascii() and lowered.isdigit():
			return int(lowered, 10)
	except ValueError:
		return None
	return None


def numeric_host_to_ipv4(host: str) -> str | None:
	"""Return the IPv4 address a numeric host stands for, if any.

	Handles the shorthand forms that ``inet_aton`` accepts, such as
	``2130706433``, ``0x7f.1`` and ``127.1``.
	"""
	labels = host.split(".")
	if not 1 <= len(labels) <= 4:
		return None
	values: list[int] = []
	for label in labels:
		value = _numeric_label_value(label)
		if value is None:
			return None
		values.append(value)

	value = 0
	for part in values[:-1]:
		if part > 0xFF:
			return None
		value = (value << 8) | part
	remaining_bytes = 4 - (len(values) - 1)
	if values[-1] >= 1 << (8 * remaining_bytes):
		return None
	value = (value << (8 * remaining_bytes)) | values[-1]

	octets = [(value >> shift) & 0xFF for shift in (24, 16, 8, 0)]
	return ".".join(str(octet) for octet in octets)


def build_host_info(parsed: ParsedURL) -> HostInfo | None:
	"""Return the public suffix, controlling domain and subdomain."""
	if not parsed.has_host or parsed.is_ip:
		return None
	if "." not in parsed.host:
		# Single-label hosts such as "localhost" or a bare number have no
		# domain ending to break down.
		return None
	try:
		suffix = psl.public_suffix(parsed.host)
		registrable = psl.registrable_domain(parsed.host)
		available = True
	except psl.DomainDataError:
		labels = parsed.host.split(".")
		suffix = labels[-1]
		registrable = ".".join(labels[-2:]) if len(labels) >= 2 else parsed.host
		available = False

	subdomain = ""
	if parsed.host != registrable and parsed.host.endswith("." + registrable):
		subdomain = parsed.host[: -(len(registrable) + 1)]
	return HostInfo(
		public_suffix=suffix,
		registrable=registrable,
		subdomain=subdomain,
		psl_available=available,
	)
