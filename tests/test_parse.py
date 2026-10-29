"""Tests for finding and splitting links."""

import unittest

from _norlay_link_checker.parse import (
	InvalidURL,
	build_host_info,
	decode_host,
	encode_host,
	extract_urls,
	numeric_host_to_ipv4,
	parse_url,
)


class ExtractURLsTests(unittest.TestCase):
	def test_finds_scheme_url_and_trims_sentence_punctuation(self):
		self.assertEqual(
			extract_urls("Please check https://example.com/path."),
			["https://example.com/path"],
		)

	def test_keeps_balanced_brackets_and_drops_unbalanced_ones(self):
		self.assertEqual(
			extract_urls("(see https://example.com/a_(b))"),
			["https://example.com/a_(b)"],
		)
		self.assertEqual(
			extract_urls("see https://example.com/path)"),
			["https://example.com/path"],
		)

	def test_finds_bare_host_inside_a_sentence(self):
		self.assertEqual(extract_urls("Go to example.com now"), ["example.com"])

	def test_finds_both_forms_in_order(self):
		self.assertEqual(
			extract_urls("example.com then https://foo.org/x"),
			["example.com", "https://foo.org/x"],
		)

	def test_ignores_email_addresses_and_plain_words(self):
		self.assertEqual(extract_urls("write to someone@example.com"), [])
		self.assertEqual(extract_urls("nothing to see here"), [])

	def test_ignores_file_names_and_dotted_words(self):
		for text in (
			"report.pdf",
			"invoice.docx",
			"photo.jpg",
			"my notes.txt",
			"hello.there",
			"meeting at 10.30 tomorrow",
		):
			with self.subTest(text=text):
				self.assertEqual(extract_urls(text), [])

	def test_still_finds_bare_hosts_with_a_known_suffix(self):
		for text in ("example.com", "www.example.co.uk", "пример.рф"):
			with self.subTest(text=text):
				self.assertEqual(extract_urls(text), [text])

	def test_does_not_duplicate_the_same_link(self):
		self.assertEqual(
			extract_urls("https://example.com and https://example.com"),
			["https://example.com"],
		)

	def test_finds_script_and_data_links(self):
		self.assertEqual(
			extract_urls("javascript:alert(1)"),
			["javascript:alert(1)"],
		)
		self.assertEqual(
			extract_urls("data:text/html,x"),
			["data:text/html,x"],
		)

	def test_empty_text_gives_no_links(self):
		self.assertEqual(extract_urls(""), [])
		self.assertEqual(extract_urls("   \n\t "), [])


class ParseURLTests(unittest.TestCase):
	def test_simple_https(self):
		parsed = parse_url("https://Example.COM/Path?q=1#part")
		self.assertEqual(parsed.scheme, "https")
		self.assertEqual(parsed.kind, "web")
		self.assertEqual(parsed.host, "example.com")
		self.assertEqual(parsed.path, "/Path")
		self.assertEqual(parsed.query, "q=1")
		self.assertEqual(parsed.fragment, "part")
		self.assertFalse(parsed.trailing_dot)

	def test_missing_scheme(self):
		parsed = parse_url("example.com/path")
		self.assertIsNone(parsed.scheme)
		self.assertEqual(parsed.kind, "web")
		self.assertEqual(parsed.host, "example.com")
		self.assertEqual(parsed.path, "/path")

	def test_host_and_port_without_scheme(self):
		parsed = parse_url("example.com:8080/x")
		self.assertIsNone(parsed.scheme)
		self.assertEqual(parsed.host, "example.com")
		self.assertEqual(parsed.port, 8080)
		self.assertIsNone(parsed.port_error)

	def test_invalid_port_is_recorded_not_raised(self):
		parsed = parse_url("https://example.com:abc/")
		self.assertEqual(parsed.port_error, "not_a_number")
		self.assertIsNone(parsed.port)

	def test_out_of_range_port(self):
		parsed = parse_url("https://example.com:99999/")
		self.assertEqual(parsed.port_error, "out_of_range")

	def test_userinfo_is_split_at_the_last_at_sign(self):
		parsed = parse_url("https://user:pass@example.com/")
		self.assertEqual(parsed.userinfo, "user:pass")
		self.assertEqual(parsed.host, "example.com")

	def test_ipv4_literal(self):
		parsed = parse_url("https://192.168.1.1:8080/")
		self.assertTrue(parsed.is_ip)
		self.assertEqual(parsed.ip_version, 4)
		self.assertEqual(parsed.port, 8080)

	def test_ipv6_literal_needs_brackets(self):
		parsed = parse_url("https://[2001:db8::1]/")
		self.assertTrue(parsed.is_ip)
		self.assertEqual(parsed.ip_version, 6)
		with self.assertRaises(InvalidURL):
			parse_url("https://2001:db8::1/")

	def test_trailing_dot_is_flagged_and_removed(self):
		parsed = parse_url("https://example.com./")
		self.assertTrue(parsed.trailing_dot)
		self.assertEqual(parsed.host, "example.com")

	def test_punycode_is_decoded_for_display(self):
		parsed = parse_url("https://xn--e1afmkfd.xn--p1ai/")
		self.assertEqual(parsed.host, "пример.рф")
		self.assertEqual(parsed.host_ascii, "xn--e1afmkfd.xn--p1ai")

	def test_backslash_is_kept_and_acts_as_separator(self):
		parsed = parse_url("https://example.com\\@evil.com")
		self.assertEqual(parsed.host, "example.com")

	def test_script_link(self):
		parsed = parse_url("javascript:alert(1)")
		self.assertEqual(parsed.kind, "script")
		self.assertEqual(parsed.scheme, "javascript")
		self.assertEqual(parsed.host, "")

	def test_email_link(self):
		parsed = parse_url("mailto:someone@example.com")
		self.assertEqual(parsed.kind, "email")
		self.assertFalse(parsed.has_host)

	def test_file_link(self):
		parsed = parse_url("file:///C:/Windows/System32/calc.exe")
		self.assertEqual(parsed.kind, "local")

	def test_empty_and_blank_are_invalid(self):
		with self.assertRaises(InvalidURL):
			parse_url("")
		with self.assertRaises(InvalidURL):
			parse_url("   ")

	def test_scheme_without_host_is_invalid(self):
		with self.assertRaises(InvalidURL):
			parse_url("https:///path")

	def test_percent_encoded_host(self):
		parsed = parse_url("https://ex%61mple.com/")
		self.assertTrue(parsed.percent_encoded_host)


class HostHelperTests(unittest.TestCase):
	def test_decode_and_encode_round_trip(self):
		self.assertEqual(decode_host("xn--e1afmkfd.xn--p1ai"), "пример.рф")
		self.assertEqual(encode_host("пример.рф"), "xn--e1afmkfd.xn--p1ai")
		self.assertEqual(decode_host("example.com"), "example.com")

	def test_numeric_host_forms(self):
		self.assertEqual(numeric_host_to_ipv4("2130706433"), "127.0.0.1")
		self.assertEqual(numeric_host_to_ipv4("0x7f000001"), "127.0.0.1")
		self.assertEqual(numeric_host_to_ipv4("127.1"), "127.0.0.1")
		self.assertEqual(numeric_host_to_ipv4("127.0.1"), "127.0.0.1")
		self.assertIsNone(numeric_host_to_ipv4("example.com"))
		self.assertIsNone(numeric_host_to_ipv4("999.1.1.1"))

	def test_host_info_for_web_address(self):
		parsed = parse_url("https://login.example.co.uk/path")
		info = build_host_info(parsed)
		self.assertEqual(info.public_suffix, "co.uk")
		self.assertEqual(info.registrable, "example.co.uk")
		self.assertEqual(info.subdomain, "login")

	def test_host_info_is_not_computed_for_ips(self):
		self.assertIsNone(build_host_info(parse_url("https://192.168.1.1/")))


if __name__ == "__main__":
	unittest.main()
