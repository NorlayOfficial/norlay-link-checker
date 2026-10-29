# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Render an :class:`Analysis` as plain text for NVDA's browse mode."""

from __future__ import annotations

import textwrap

from .i18n import _
from .model import NOTE, WARNING, Analysis, Finding, ParsedURL
from .parse import MAX_URL_CHARS
from .unicode_utils import escape_for_display

_WIDTH = 76

def _kind_label(kind: str) -> str | None:
	"""Return a display label for non-web links, or ``None``.

	The labels are looked up lazily so that the translation function can be
	installed after this module is imported.
	"""
	if kind == "email":
		return _("Email address link")
	if kind == "phone":
		return _("Phone number link")
	if kind == "script":
		return _("Script link")
	if kind == "data":
		return _("Embedded data link")
	if kind == "local":
		return _("Local file link")
	if kind == "other":
		return _("Other kind of link")
	return None


def _protocol_text(parsed: ParsedURL) -> str:
	if parsed.scheme is None:
		return _("Not given")
	if parsed.scheme == "https":
		return _("HTTPS (encrypted)")
	if parsed.scheme == "http":
		return _("HTTP (not encrypted)")
	return parsed.scheme.upper()


def _count_phrase(warnings: int, notes: int) -> str:
	"""Return ``2 warnings, 1 note`` or an empty string."""
	pieces: list[str] = []
	if warnings == 1:
		pieces.append(_("1 warning"))
	elif warnings > 1:
		pieces.append(_("{count} warnings").format(count=warnings))
	if notes == 1:
		pieces.append(_("1 note"))
	elif notes > 1:
		pieces.append(_("{count} notes").format(count=notes))
	return ", ".join(pieces)


def short_summary(analysis: Analysis) -> str:
	"""One spoken sentence describing the link and the number of findings."""
	parsed = analysis.parsed
	sentences: list[str] = []

	if parsed.kind in ("email", "phone", "script", "data", "local", "other"):
		sentences.append((_kind_label(parsed.kind) or "") + ".")
	elif parsed.scheme == "https":
		sentences.append(_("HTTPS link."))
	elif parsed.scheme == "http":
		sentences.append(_("HTTP link, not encrypted."))
	elif parsed.scheme is None:
		sentences.append(_("Link with no protocol."))
	else:
		sentences.append(
			_("{scheme} link.").format(scheme=(parsed.scheme or "").upper()),
		)

	if parsed.kind == "web" and parsed.has_host:
		if analysis.host_info and analysis.host_info.registrable:
			sentences.append(
				_("Controlling domain: {domain}.").format(
					domain=escape_for_display(analysis.host_info.registrable, 80),
				),
			)
		elif parsed.is_ip:
			sentences.append(_("The host is an IP address."))
		else:
			sentences.append(
				_("Host: {host}.").format(host=escape_for_display(parsed.host, 80)),
			)

	counts = _count_phrase(analysis.warning_count, analysis.note_count)
	if counts:
		sentences.append(counts + ".")
	else:
		sentences.append(_("No suspicious patterns found."))

	return " ".join(sentences)


def _address_lines(analysis: Analysis) -> list[str]:
	parsed = analysis.parsed
	label = _kind_label(parsed.kind)
	if label is not None:
		lines = [
			_("As copied: {url}").format(url=escape_for_display(parsed.raw, 300)),
			_("Type: {kind}").format(kind=label),
			_("Scheme: {scheme}").format(scheme=parsed.scheme or ""),
		]
		return lines

	lines = [
		_("As copied: {url}").format(url=escape_for_display(parsed.raw, 300)),
		_("Protocol: {protocol}").format(protocol=_protocol_text(parsed)),
		_("Host: {host}").format(host=escape_for_display(parsed.host, 200)),
	]
	if parsed.is_ip:
		lines.append(
			_("Controlling domain: not applicable, because the host is an IP address"),
		)
	elif analysis.host_info and analysis.host_info.registrable:
		lines.append(
			_("Controlling domain: {domain}").format(
				domain=escape_for_display(analysis.host_info.registrable, 200),
			),
		)
		if analysis.host_info.subdomain:
			lines.append(
				_("Subdomain: {subdomain}").format(
					subdomain=escape_for_display(analysis.host_info.subdomain, 200),
				),
			)
	else:
		lines.append(
			_("Controlling domain: not applicable, because the host has no domain ending"),
		)

	if parsed.userinfo is not None:
		lines.append(_("User name before the at sign: present"))

	if parsed.port_error:
		lines.append(_("Port: invalid"))
	elif parsed.port is not None:
		lines.append(_("Port: {port}").format(port=parsed.port))

	if analysis.truncated:
		lines.append(
			_(
				"Only the first {limit} characters were checked.",
			).format(limit=MAX_URL_CHARS),
		)
	return lines


def _render_finding(finding: Finding, number: int) -> str:
	prefix = f"  {number}. "
	return textwrap.fill(
		finding.message,
		width=_WIDTH,
		initial_indent=prefix,
		subsequent_indent=" " * len(prefix),
	)


def _heading(title: str, body: str) -> str:
	return f"{title}\n{body}"


def _paragraph(text: str) -> str:
	return textwrap.fill(
		text,
		width=_WIDTH,
		initial_indent="  ",
		subsequent_indent="  ",
	)


def render_report(analysis: Analysis) -> str:
	"""Return the complete report as plain text.

	The caller passes this to ``ui.browseableMessage`` with ``isHtml=False`` so
	that nothing in the copied address can be interpreted as markup.
	"""
	parsed = analysis.parsed
	blocks: list[str] = [_("Norlay Link Checker")]

	blocks.append(_("Summary: {summary}").format(summary=short_summary(analysis)))

	if analysis.url_count > 1:
		blocks.append(
			_(
				"The clipboard contained {count} links. This report covers the first "
				"one.",
			).format(count=analysis.url_count),
		)

	blocks.append(
		_heading(
			_("Address"),
			"\n".join("  " + line for line in _address_lines(analysis)),
		),
	)

	warnings = [finding for finding in analysis.findings if finding.severity == WARNING]
	notes = [finding for finding in analysis.findings if finding.severity == NOTE]

	if warnings:
		blocks.append(
			_heading(
				_("Warnings"),
				"\n".join(
					_render_finding(finding, number)
					for number, finding in enumerate(warnings, start=1)
				),
			),
		)

	if notes:
		blocks.append(
			_heading(
				_("Notes"),
				"\n".join(
					_render_finding(finding, number)
					for number, finding in enumerate(notes, start=1)
				),
			),
		)

	if parsed.kind == "web":
		explanation = _paragraph(
			_(
				"These are patterns that are often used in phishing and lookalike "
				"addresses. They do not prove that the link is dangerous, and a "
				"link with no warnings is not proof that it is safe. If you did not "
				"expect this link, open the organisation's official app or type its "
				"address yourself instead of using the link.",
			),
		)
	else:
		explanation = _paragraph(
			_(
				"This is not a website address, so there is no domain to compare. "
				"The link was not opened. Treat it with the same care as any "
				"unexpected message.",
			),
		)
	blocks.append(_heading(_("What this means"), explanation))

	blocks.append(
		_heading(
			_("Privacy"),
			_paragraph(
				_(
					"Checked on this computer. The address was not sent anywhere, not "
					"saved, and not opened.",
				),
			),
		),
	)

	return "\n\n".join(blocks) + "\n"
