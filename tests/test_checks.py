"""Tests for the individual checks and the wording they produce."""

import unittest

from _norlay_link_checker import analyze


def codes(url: str) -> set[str]:
	return {finding.code for finding in analyze(url).findings}


def findings(url: str):
	return analyze(url).findings


class SchemeTests(unittest.TestCase):
	def test_https_is_clean(self):
		self.assertEqual(codes("https://example.com/"), set())

	def test_http_warns_about_encryption(self):
		self.assertIn("scheme_http", codes("http://example.com/"))

	def test_missing_scheme_is_a_note(self):
		self.assertIn("scheme_missing", codes("example.com"))

	def test_file_links_warn(self):
		self.assertIn("scheme_file", codes("file:///C:/Windows/System32/calc.exe"))

	def test_script_links_warn(self):
		self.assertIn("scheme_script", codes("javascript:alert(1)"))
		self.assertIn("scheme_script", codes("vbscript:msgbox(1)"))

	def test_data_links_warn(self):
		self.assertIn("scheme_data", codes("data:text/html,x"))

	def test_email_links_have_no_host_checks(self):
		self.assertEqual(codes("mailto:someone@example.com"), set())


class AddressStructureTests(unittest.TestCase):
	def test_public_ip_address(self):
		codes_for_link = codes("https://8.8.8.8/")
		self.assertIn("ip_literal", codes_for_link)
		self.assertNotIn("ip_private", codes_for_link)

	def test_private_ip_address(self):
		codes_for_link = codes("https://192.168.1.1/")
		self.assertIn("ip_literal", codes_for_link)
		self.assertIn("ip_private", codes_for_link)

	def test_numeric_host_names_the_equivalent_address(self):
		messages = [finding.message for finding in findings("https://2130706433/")]
		self.assertIn("ip_numeric", {finding.code for finding in findings("https://2130706433/")})
		self.assertTrue(any("127.0.0.1" in message for message in messages))

	def test_userinfo_is_explained(self):
		self.assertIn("userinfo", codes("https://user:pass@example.com/"))

	def test_nonstandard_port_is_a_note(self):
		self.assertIn("nonstandard_port", codes("https://example.com:8443/"))

	def test_bad_port_is_reported(self):
		self.assertIn("port_not_a_number", codes("https://example.com:abc/"))
		self.assertIn("port_out_of_range", codes("https://example.com:99999/"))

	def test_trailing_dot(self):
		self.assertIn("trailing_dot", codes("https://example.com./"))


class LookalikeTests(unittest.TestCase):
	def test_punycode_shows_decoded_name(self):
		messages = [finding.message for finding in findings("https://xn--e1afmkfd.xn--p1ai/")]
		self.assertIn("punycode", codes("https://xn--e1afmkfd.xn--p1ai/"))
		self.assertTrue(any("пример.рф" in message for message in messages))

	def test_unicode_host_is_reported(self):
		self.assertIn("unicode_host", codes("https://пример.рф/"))

	def test_mixed_alphabet_is_reported(self):
		self.assertIn("mixed_script", codes("https://\u0430pple.com/"))

	def test_bidi_control_is_reported(self):
		self.assertIn("bidi_control", codes("https://example.com/\u202eevil"))

	def test_zero_width_character_is_reported(self):
		self.assertIn("zero_width", codes("https://exa\u200bmple.com/"))

	def test_control_character_is_reported(self):
		self.assertIn("control_char", codes("https://example.com/\x07"))


class DomainDisguiseTests(unittest.TestCase):
	def test_domain_ending_in_subdomain(self):
		codes_for_link = codes("https://paypal.com.evil.com/")
		self.assertIn("tld_in_subdomain", codes_for_link)
		self.assertIn("brand_in_address", codes_for_link)

	def test_brand_in_hyphenated_domain(self):
		self.assertIn("brand_in_address", codes("https://paypal-login.com/"))

	def test_brand_in_subdomain(self):
		self.assertIn("brand_in_address", codes("https://microsoft.login.example.com/"))

	def test_official_domain_is_not_flagged(self):
		self.assertNotIn("brand_in_address", codes("https://www.paypal.com/"))
		self.assertNotIn("brand_in_address", codes("https://login.microsoft.com/"))

	def test_official_country_domain_is_not_flagged(self):
		self.assertNotIn("brand_in_address", codes("https://www.google.co.uk/"))

	def test_github_pages_is_not_flagged(self):
		self.assertNotIn("brand_in_address", codes("https://user.github.io/project"))

	def test_many_subdomains(self):
		self.assertIn("many_subdomains", codes("https://a.b.c.d.e.f.example.com/"))
		self.assertIn("many_subdomains_note", codes("https://a.b.c.example.com/"))


class PatternTests(unittest.TestCase):
	def test_shortener_is_a_note(self):
		self.assertIn("shortener", codes("https://bit.ly/3abc"))

	def test_long_address_warns(self):
		self.assertIn("long_url", codes("https://example.com/" + "a" * 200))

	def test_moderately_long_address_is_a_note(self):
		self.assertIn("long_url_note", codes("https://example.com/" + "a" * 90))

	def test_backslash(self):
		self.assertIn("backslash", codes("https://example.com\\@evil.com"))

	def test_hosting_suffix_is_used_for_the_controlling_domain(self):
		analysis = analyze("https://user.github.io/project")
		self.assertEqual(analysis.host_info.registrable, "user.github.io")
		self.assertEqual(analysis.host_info.public_suffix, "github.io")


class SeverityTests(unittest.TestCase):
	def test_http_is_a_warning(self):
		severities = {finding.severity for finding in findings("http://example.com/")}
		self.assertEqual(severities, {"warning"})

	def test_missing_scheme_is_a_note(self):
		severities = {finding.severity for finding in findings("example.com")}
		self.assertEqual(severities, {"note"})


if __name__ == "__main__":
	unittest.main()
