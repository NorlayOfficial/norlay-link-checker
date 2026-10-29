# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Pure check functions.

Each check looks at a parsed link and returns zero or more findings.  Checks
never raise for unusual input and never use the network.  A finding explains
what was seen and why it can matter; it is never a verdict about the site.
"""

from __future__ import annotations

import ipaddress
import os

from .i18n import _
from .model import NOTE, WARNING, Finding, HostInfo, ParsedURL
from .parse import numeric_host_to_ipv4
from .unicode_utils import (
	compatible_form,
	describe_character,
	escape_for_display,
	has_confusable_mix,
	is_bidi_control,
	is_control,
	is_zero_width,
)

DATA_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

#: Labels that are too generic to treat as a brand impersonation on their own.
_SAFE_PRECEDING_LABELS = frozenset({
	"www", "m", "wap", "mail", "smtp", "pop", "imap", "webmail", "email",
	"api", "cdn", "static", "img", "images", "assets", "media", "docs",
	"help", "support", "status", "blog", "news", "dev", "test", "staging",
})

_COMMON_TLDS = frozenset({
	"com", "net", "org", "co", "uk", "us", "de", "fr", "io", "app", "dev",
	"info", "biz", "xyz", "online", "site", "shop", "store", "click", "link",
	"ru", "cn", "br", "in", "au", "ca", "jp", "nl", "se", "no", "es", "it",
	"pl", "ch", "at", "be", "dk", "fi", "ie", "nz", "za", "mx", "ar", "tr",
	"sa", "ae", "sg", "hk", "kr", "tw", "eu", "me", "tv", "cc", "live",
})

#: Domains that host user content.  Used to avoid treating a shared hosting
#: suffix as if it were a site owner's own brand name.
_SHARED_HOSTING = frozenset({
	"github.io", "gitlab.io", "netlify.app", "vercel.app", "pages.dev",
	"workers.dev", "blogspot.com", "wordpress.com", "herokuapp.com",
	"azurewebsites.net", "cloudfront.net", "firebaseapp.com", "web.app",
	"notion.site", "readthedocs.io", "surge.sh", "glitch.me", "repl.co",
})

_brands: tuple[tuple[str, str, str, str], ...] | None = None
_shorteners: frozenset[str] | None = None


def _read_data_file(filename: str) -> list[str]:
	path = os.path.join(DATA_DIRECTORY, filename)
	try:
		with open(path, encoding="utf-8") as handle:
			return handle.read().splitlines()
	except OSError:
		return []


def _load_brands() -> tuple[tuple[str, str, str, str], ...]:
	global _brands
	if _brands is not None:
		return _brands
	entries: list[tuple[str, str, str, str]] = []
	for line in _read_data_file("brands.txt"):
		line = line.strip()
		if not line or line.startswith("#"):
			continue
		parts = [part.strip() for part in line.split("|")]
		if len(parts) < 3:
			continue
		token = parts[0].lower()
		official = parts[1].lower()
		display = parts[2]
		confidence = parts[3].lower() if len(parts) > 3 else "high"
		if token and official:
			entries.append((token, official, display, confidence))
	_brands = tuple(entries)
	return _brands


def _load_shorteners() -> frozenset[str]:
	global _shorteners
	if _shorteners is not None:
		return _shorteners
	domains = set()
	for line in _read_data_file("shorteners.txt"):
		line = line.strip().lower()
		if not line or line.startswith("#"):
			continue
		domains.add(line)
	_shorteners = frozenset(domains)
	return _shorteners


def _controlled_labels(parsed: ParsedURL, host_info: HostInfo | None) -> list[str]:
	"""Labels that the site owner chose, excluding the public suffix."""
	host = parsed.host
	suffix = host_info.public_suffix if host_info else ""
	if suffix and host.endswith("." + suffix):
		prefix = host[: -(len(suffix) + 1)]
		return prefix.split(".") if prefix else []
	return host.split(".")


def _subdomain_labels(parsed: ParsedURL, host_info: HostInfo | None) -> list[str]:
	if not host_info or not host_info.subdomain:
		return []
	return [label for label in host_info.subdomain.split(".") if label]


def _host_owns_brand(registrable: str, official: str, brand: str) -> bool:
	"""True when the controlling domain is plausibly the brand's own.

	The first label of the registrable domain is what matters, so country
	domains such as ``google.co.uk`` are treated as owned by the brand.
	"""
	if registrable == official or registrable.endswith("." + official):
		return True
	return registrable.split(".")[0] == brand


def check_scheme(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	scheme = parsed.scheme
	if scheme == "https":
		return []
	if scheme is None:
		return [
			Finding(
				"scheme_missing",
				NOTE,
				_(
					"No protocol is given, so the address itself does not say whether "
					"the connection will be encrypted. Browsers usually try HTTPS "
					"first, but the site may still use HTTP.",
				),
			),
		]
	if scheme == "http":
		return [
			Finding(
				"scheme_http",
				WARNING,
				_(
					"This link uses HTTP, which is not encrypted. Someone on the "
					"network may be able to read or change what is sent. Prefer HTTPS "
					"when the site offers it.",
				),
			),
		]
	if scheme in ("ftp", "ftps"):
		return [
			Finding(
				"scheme_ftp",
				WARNING,
				_(
					"This link uses FTP, an old file-transfer protocol, not a normal "
					"web page. FTP is usually not encrypted.",
				),
			),
		]
	if scheme == "file":
		return [
			Finding(
				"scheme_file",
				WARNING,
				_(
					"This is a link to a file on this computer, not to a website. "
					"Opening it may run or reveal a local file.",
				),
			),
		]
	if scheme in ("javascript", "vbscript"):
		return [
			Finding(
				"scheme_script",
				WARNING,
				_(
					"This is not an ordinary website link. It contains a script, which "
					"can hide what it will do. The contents are not shown here.",
				),
			),
		]
	if scheme == "data":
		return [
			Finding(
				"scheme_data",
				WARNING,
				_(
					"This is a data link, not a website. Its content is embedded in the "
					"address itself, so the real destination cannot be shown.",
				),
			),
		]
	if scheme == "blob":
		return [
			Finding(
				"scheme_blob",
				WARNING,
				_(
					"This is a browser-generated blob link. It only works inside the "
					"page that created it and can hide the real address.",
				),
			),
		]
	return []


def check_control_characters(
	parsed: ParsedURL,
	host_info: HostInfo | None,
) -> list[Finding]:
	findings: list[Finding] = []
	raw = parsed.raw

	bidi = [character for character in raw if is_bidi_control(character)]
	if bidi:
		example = describe_character(bidi[0])
		findings.append(
			Finding(
				"bidi_control",
				WARNING,
				_(
					"The address contains {count} invisible direction-control "
					"character(s), for example {example}. They can make the address "
					"appear in a different order from the one actually used.",
				).format(count=len(bidi), example=example),
			),
		)

	zero_width = [character for character in raw if is_zero_width(character)]
	if zero_width:
		findings.append(
			Finding(
				"zero_width",
				WARNING,
				_(
					"The address contains {count} invisible character(s) that are not "
					"normally part of a web address.",
				).format(count=len(zero_width)),
			),
		)

	controls = [character for character in raw if is_control(character)]
	if controls:
		findings.append(
			Finding(
				"control_char",
				WARNING,
				_(
					"The address contains {count} control character(s), which are not "
					"valid in a normal web address.",
				).format(count=len(controls)),
			),
		)

	if "\\" in raw:
		findings.append(
			Finding(
				"backslash",
				WARNING,
				_(
					"The address contains a backslash. Browsers may treat it like a "
					"forward slash, which can make the real destination different from "
					"what it appears to be.",
				),
			),
		)

	return findings


def check_length(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	length = len(parsed.raw)
	if length >= 200:
		return [
			Finding(
				"long_url",
				WARNING,
				_(
					"This address is {length} characters long. Very long addresses can "
					"hide the part that identifies the site, especially on a small "
					"screen.",
				).format(length=length),
			),
		]
	if length >= 100:
		return [
			Finding(
				"long_url_note",
				NOTE,
				_(
					"This address is {length} characters long. Many legitimate "
					"tracking and shopping links are long, but check the part just "
					"before the first single slash.",
				).format(length=length),
			),
		]
	return []


def check_long_query(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if parsed.query and len(parsed.query) >= 120:
		return [
			Finding(
				"long_query",
				NOTE,
				_(
					"This address has a long query string after the question mark. "
					"Query strings are often used for tracking and can hide where the "
					"link really goes.",
				),
			),
		]
	return []


def check_userinfo(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if parsed.userinfo is None:
		return []
	return [
		Finding(
			"userinfo",
			WARNING,
			_(
				"Everything before the at sign is a user name, not the site. The real "
				"site is the part after it. This pattern is often used to make a link "
				"look as if it goes somewhere else.",
			),
		),
	]


def check_ip_literal(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if not parsed.is_ip:
		return []
	findings = [
		Finding(
			"ip_literal",
			WARNING,
			_(
				"The site address is an IP address, not a name. That is normal for "
				"routers and internal networks, but public websites usually use names.",
			),
		),
	]
	host = parsed.host.split("%", 1)[0]
	private = False
	try:
		address = ipaddress.ip_address(host)
		private = address.is_private or address.is_loopback or address.is_link_local
	except ValueError:
		pass
	if private:
		findings.append(
			Finding(
				"ip_private",
				NOTE,
				_(
					"This is a private or local network address, so it probably points "
					"to a device on your own network rather than to the internet.",
				),
			),
		)
	return findings


def check_numeric_host(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if parsed.is_ip or not parsed.has_host:
		return []
	equivalent = numeric_host_to_ipv4(parsed.host)
	if equivalent is None:
		return []
	return [
		Finding(
			"ip_numeric",
			WARNING,
			_(
				"The address looks like a number rather than a name. It is equivalent "
				"to the IP address {address}, written in an unusual form.",
			).format(address=equivalent),
		),
	]


def check_punycode(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if not parsed.has_host:
		return []
	labels = parsed.host_input.lower().split(".")
	if not any(label.startswith("xn--") for label in labels):
		return []
	shown = escape_for_display(parsed.host, 120)
	if parsed.host == parsed.host_input.lower():
		return [
			Finding(
				"punycode_undecodable",
				WARNING,
				_(
					"The address uses a punycode domain name that could not be decoded. "
					"Punycode is how international names are written in plain ASCII.",
				),
			),
		]
	return [
		Finding(
			"punycode",
			WARNING,
			_(
				"The address uses an internationalised domain name, written here as "
				"punycode. The name it represents is {shown}. International names are "
				"legitimate, but lookalike letters can imitate another site.",
			).format(shown=shown),
		),
	]


def check_unicode_host(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if not parsed.has_host:
		return []
	if parsed.host_ascii == parsed.host:
		return []
	labels = parsed.host_input.lower().split(".")
	if any(label.startswith("xn--") for label in labels):
		return []
	return [
		Finding(
			"unicode_host",
			WARNING,
			_(
				"The address contains non-English characters. That is normal for many "
				"sites, but some characters look almost identical to Latin letters. "
				"Its ASCII form is {ascii_form}.",
			).format(ascii_form=escape_for_display(parsed.host_ascii, 120)),
		),
	]


def check_mixed_script(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if not parsed.has_host:
		return []
	for label in parsed.host.split("."):
		if has_confusable_mix(label):
			return [
				Finding(
					"mixed_script",
					WARNING,
					_(
						"The domain name mixes Latin letters with letters from another "
						"alphabet. Lookalike letters from another alphabet are a common "
						"way to imitate a familiar name.",
					),
				),
			]
	return []


def check_compatibility_characters(
	parsed: ParsedURL,
	host_info: HostInfo | None,
) -> list[Finding]:
	if not parsed.has_host:
		return []
	normalised = compatible_form(parsed.host)
	if normalised == parsed.host or not normalised.isascii():
		return []
	return [
		Finding(
			"compat_chars",
			WARNING,
			_(
				"The address uses full-width or compatibility characters that "
				"normalise to {normalised}. It may be an attempt to look like an "
				"ordinary address.",
			).format(normalised=escape_for_display(normalised, 120)),
		),
	]


def check_host_length(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if not parsed.has_host:
		return []
	too_long = len(parsed.host) > 253 or any(
		len(label) > 63 for label in parsed.host.split(".")
	)
	if not too_long:
		return []
	return [
		Finding(
			"long_host",
			WARNING,
			_(
				"Part of the host name is longer than the standard allows. The address "
				"is malformed or deliberately unusual.",
			),
		),
	]


def check_trailing_dot(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if not parsed.trailing_dot:
		return []
	return [
		Finding(
			"trailing_dot",
			NOTE,
			_(
				"The host name ends with a dot. This is technically valid but unusual, "
				"and some software displays it differently.",
			),
		),
	]


def check_percent_encoded_host(
	parsed: ParsedURL,
	host_info: HostInfo | None,
) -> list[Finding]:
	if not parsed.percent_encoded_host or parsed.is_ip:
		return []
	return [
		Finding(
			"encoded_host",
			WARNING,
			_(
				"The host name contains percent-encoded characters, which can hide "
				"the real name.",
			),
		),
	]


def check_port(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	findings: list[Finding] = []
	if parsed.port_error == "not_a_number":
		findings.append(
			Finding(
				"port_not_a_number",
				WARNING,
				_(
					"The port in this address is not a number. The address is malformed.",
				),
			),
		)
	elif parsed.port_error == "out_of_range":
		findings.append(
			Finding(
				"port_out_of_range",
				WARNING,
				_(
					"The port number is out of range. Valid ports are between 1 and "
					"65535.",
				),
			),
		)
	elif parsed.port_error == "empty":
		findings.append(
			Finding(
				"port_empty",
				NOTE,
				_("The address has a colon after the host name but no port number."),
			),
		)

	if parsed.port is not None:
		if parsed.port not in (80, 443):
			findings.append(
				Finding(
					"nonstandard_port",
					NOTE,
					_(
						"The link uses port {port} instead of the usual 80 or 443. This "
						"is unusual for a public website.",
					).format(port=parsed.port),
				),
			)
		elif parsed.scheme == "https" and parsed.port == 80:
			findings.append(
				Finding(
					"port_scheme_mismatch",
					NOTE,
					_(
						"The link asks for HTTPS on port 80, which is normally used for "
						"unencrypted HTTP.",
					),
				),
			)
		elif parsed.scheme == "http" and parsed.port == 443:
			findings.append(
				Finding(
					"port_scheme_mismatch",
					NOTE,
					_(
						"The link asks for HTTP on port 443, which is normally used for "
						"encrypted HTTPS.",
					),
				),
			)
	return findings


def check_tld_in_subdomain(
	parsed: ParsedURL,
	host_info: HostInfo | None,
) -> list[Finding]:
	labels = _subdomain_labels(parsed, host_info)
	if len(labels) < 2:
		return []
	for index in range(len(labels) - 1):
		next_label = labels[index + 1]
		if next_label not in _COMMON_TLDS:
			continue
		if labels[index] in _SAFE_PRECEDING_LABELS:
			continue
		imitation = ".".join(labels[index : index + 2])
		return [
			Finding(
				"tld_in_subdomain",
				WARNING,
				_(
					"The host name contains {imitation} inside the subdomain. Only the "
					"controlling domain identifies the site; words before it are chosen "
					"by whoever owns that domain.",
				).format(imitation=escape_for_display(imitation, 80)),
			),
		]
	return []


def check_many_subdomains(
	parsed: ParsedURL,
	host_info: HostInfo | None,
) -> list[Finding]:
	count = len(_subdomain_labels(parsed, host_info))
	if count >= 6:
		return [
			Finding(
				"many_subdomains",
				WARNING,
				_(
					"The address has {count} subdomain levels. Unusually deep chains are "
					"hard to read and are sometimes used to bury the real domain.",
				).format(count=count),
			),
		]
	if count >= 3:
		return [
			Finding(
				"many_subdomains_note",
				NOTE,
				_(
					"The address has {count} subdomain levels. Only the controlling "
					"domain identifies the owner.",
				).format(count=count),
			),
		]
	return []


def check_brand_in_address(
	parsed: ParsedURL,
	host_info: HostInfo | None,
) -> list[Finding]:
	if not parsed.has_host or not host_info:
		return []
	if host_info.public_suffix in _SHARED_HOSTING and parsed.host == host_info.public_suffix:
		return []

	labels = _controlled_labels(parsed, host_info)
	tokens: set[str] = set()
	for label in labels:
		for part in label.split("-"):
			if part:
				tokens.add(part.lower())
	if not tokens:
		return []

	for brand, official, display, confidence in _load_brands():
		if brand not in tokens:
			continue
		if _host_owns_brand(host_info.registrable, official, brand):
			continue
		severity = WARNING if confidence == "high" else NOTE
		message = _(
			"The name {brand} appears in the address, but the controlling domain is "
			"{registrable}, not {official}. A brand name in a subdomain or in a "
			"hyphenated domain does not mean the site belongs to that brand.",
		).format(
			brand=display,
			registrable=escape_for_display(host_info.registrable, 80),
			official=official,
		)
		return [Finding("brand_in_address", severity, message)]
	return []


def check_shortener(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	if not host_info:
		return []
	if host_info.registrable not in _load_shorteners():
		return []
	return [
		Finding(
			"shortener",
			NOTE,
			_(
				"The link uses a shortening service, so the real destination is hidden "
				"until the link is opened. This add-on cannot reveal it offline.",
			),
		),
	]


def check_psl_available(
	parsed: ParsedURL,
	host_info: HostInfo | None,
) -> list[Finding]:
	if host_info is None or host_info.psl_available:
		return []
	return [
		Finding(
			"psl_unavailable",
			NOTE,
			_(
				"The bundled domain list could not be read, so the domain breakdown is "
				"approximate. The other checks still ran.",
			),
		),
	]


_CHECK_ORDER = {
	"scheme_http": 10,
	"scheme_script": 11,
	"scheme_data": 12,
	"scheme_blob": 13,
	"scheme_file": 14,
	"scheme_ftp": 15,
	"scheme_missing": 16,
	"script": 18,
	"userinfo": 20,
	"ip_literal": 30,
	"ip_numeric": 31,
	"bidi_control": 40,
	"zero_width": 41,
	"control_char": 42,
	"backslash": 43,
	"punycode": 50,
	"punycode_undecodable": 51,
	"unicode_host": 52,
	"mixed_script": 53,
	"compat_chars": 54,
	"encoded_host": 55,
	"tld_in_subdomain": 60,
	"brand_in_address": 61,
	"many_subdomains": 62,
	"many_subdomains_note": 63,
	"long_url": 70,
	"long_url_note": 71,
	"long_query": 72,
	"long_host": 73,
	"port_not_a_number": 80,
	"port_out_of_range": 81,
	"port_empty": 82,
	"nonstandard_port": 83,
	"port_scheme_mismatch": 84,
	"shortener": 90,
	"trailing_dot": 95,
	"ip_private": 96,
	"psl_unavailable": 99,
}

_TEXT_CHECKS = (
	check_scheme,
	check_control_characters,
	check_length,
	check_long_query,
)

_HOST_CHECKS = (
	check_userinfo,
	check_ip_literal,
	check_numeric_host,
	check_port,
	check_host_length,
	check_trailing_dot,
	check_percent_encoded_host,
	check_punycode,
	check_unicode_host,
	check_mixed_script,
	check_compatibility_characters,
	check_tld_in_subdomain,
	check_many_subdomains,
	check_brand_in_address,
	check_shortener,
	check_psl_available,
)


def run_checks(parsed: ParsedURL, host_info: HostInfo | None) -> list[Finding]:
	"""Run every applicable check and return findings in display order."""
	findings: list[Finding] = []
	for check in _TEXT_CHECKS:
		findings.extend(check(parsed, host_info))
	if parsed.kind == "web" and parsed.has_host:
		for check in _HOST_CHECKS:
			findings.extend(check(parsed, host_info))

	def sort_key(finding: Finding) -> tuple[int, int, str]:
		return (
			0 if finding.severity == WARNING else 1,
			_CHECK_ORDER.get(finding.code, 500),
			finding.code,
		)

	findings.sort(key=sort_key)
	return findings
