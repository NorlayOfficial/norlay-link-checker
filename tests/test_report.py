"""Tests for the plain-text report and its wording."""

import re
import unittest

from _norlay_link_checker import analyze, render_report, short_summary


def report(url: str) -> str:
	return render_report(analyze(url))


class StructureTests(unittest.TestCase):
	def test_clean_report_has_the_expected_sections(self):
		text = report("https://example.com/")
		for heading in ("Norlay Link Checker", "Summary:", "Address", "What this means", "Privacy"):
			self.assertIn(heading, text)
		self.assertNotIn("\nWarnings\n", text)
		self.assertNotIn("\nNotes\n", text)

	def test_clean_summary_says_no_patterns_were_found(self):
		summary = short_summary(analyze("https://example.com/"))
		self.assertIn("HTTPS link", summary)
		self.assertIn("example.com", summary)
		self.assertIn("No suspicious patterns found", summary)
		self.assertEqual(len(summary.splitlines()), 1)

	def test_warning_report_lists_warnings(self):
		text = report("http://192.168.1.1/")
		self.assertIn("\nWarnings\n", text)
		self.assertIn("not encrypted", text)
		self.assertIn("IP address", text)

	def test_address_block_reports_domain_and_subdomain(self):
		text = report("https://login.example.co.uk/path")
		self.assertIn("Protocol: HTTPS (encrypted)", text)
		self.assertIn("Controlling domain: example.co.uk", text)
		self.assertIn("Subdomain: login", text)

	def test_email_report_is_not_treated_as_a_website(self):
		text = report("mailto:someone@example.com")
		self.assertIn("Type: Email address link", text)
		self.assertNotIn("Controlling domain", text)

	def test_multiple_links_are_mentioned(self):
		text = report("https://one.example https://two.example")
		self.assertIn("contained 2 links", text)
		self.assertIn("first one", text)

	def test_truncation_is_reported(self):
		text = report("https://example.com/" + "a" * 9000)
		self.assertIn("Only the first 8192 characters were checked.", text)

	def test_bidi_characters_are_made_visible(self):
		text = report("https://example.com/\u202eevil")
		self.assertIn("<U+202E>", text)


class WordingTests(unittest.TestCase):
	def test_uncertainty_paragraph_is_always_present(self):
		for url in (
			"https://example.com/",
			"http://192.168.1.1/",
			"https://xn--e1afmkfd.xn--p1ai/",
			"https://paypal.com.evil.com/",
		):
			with self.subTest(url=url):
				text = report(url)
				self.assertIn("not proof that it is safe", text)
				self.assertIn("do not prove that the link is dangerous", text)

	def test_no_verdict_language(self):
		"""The word "safe" may appear only in the uncertainty paragraph."""
		for url in (
			"https://example.com/",
			"https://paypal.com.evil.com/",
		):
			with self.subTest(url=url):
				text = report(url)
				self.assertNotIn("malicious", text.lower())
				self.assertEqual(text.lower().count("safe"), 1)
				self.assertIn("not proof that it is safe", text)
				verdict = re.compile(
					r"(?m)^\s*(?:safe|malicious|dangerous)\s*[.!]?$",
					re.IGNORECASE,
				)
				self.assertIsNone(verdict.search(text))

	def test_non_web_report_has_no_verdict(self):
		text = report("javascript:alert(1)")
		self.assertNotIn("safe", text.lower())
		self.assertNotIn("malicious", text.lower())

	def test_every_finding_explains_itself(self):
		analysis = analyze("http://paypal.com.evil.com/")
		self.assertTrue(analysis.findings)
		for finding in analysis.findings:
			with self.subTest(code=finding.code):
				self.assertGreater(len(finding.message), 40)
				self.assertTrue(finding.message.rstrip().endswith((".", "?")))

	def test_privacy_line_promises_offline_check(self):
		text = report("https://example.com/")
		self.assertIn("not sent anywhere", text)
		self.assertIn("not opened", text)


if __name__ == "__main__":
	unittest.main()
