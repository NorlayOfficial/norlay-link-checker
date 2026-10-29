"""Tests for the bundled Public Suffix List lookup."""

import unittest

from _norlay_link_checker import psl


class PublicSuffixTests(unittest.TestCase):
	def test_plain_domain(self):
		self.assertEqual(psl.public_suffix("example.com"), "com")
		self.assertEqual(psl.registrable_domain("example.com"), "example.com")

	def test_multi_label_suffix(self):
		self.assertEqual(psl.public_suffix("login.example.co.uk"), "co.uk")
		self.assertEqual(psl.registrable_domain("login.example.co.uk"), "example.co.uk")

	def test_subdomain_of_multi_label_suffix(self):
		self.assertEqual(psl.registrable_domain("a.b.c.example.co.uk"), "example.co.uk")

	def test_private_suffix_is_treated_as_a_suffix(self):
		# github.io is in the private section of the list, so each user gets a
		# registrable domain of their own.
		self.assertEqual(psl.public_suffix("user.github.io"), "github.io")
		self.assertEqual(psl.registrable_domain("user.github.io"), "user.github.io")

	def test_amazon_s3_style_suffix(self):
		self.assertEqual(psl.public_suffix("bucket.s3.amazonaws.com"), "s3.amazonaws.com")
		self.assertEqual(
			psl.registrable_domain("bucket.s3.amazonaws.com"),
			"bucket.s3.amazonaws.com",
		)

	def test_wildcard_rule(self):
		# The list contains "*.ck" and "!www.ck".
		self.assertEqual(psl.registrable_domain("foo.bar.ck"), "foo.bar.ck")
		self.assertEqual(psl.public_suffix("bar.ck"), "bar.ck")

	def test_exception_rule(self):
		self.assertEqual(psl.public_suffix("www.ck"), "ck")
		self.assertEqual(psl.registrable_domain("www.ck"), "www.ck")
		self.assertEqual(psl.public_suffix("city.kawasaki.jp"), "kawasaki.jp")
		self.assertEqual(
			psl.registrable_domain("city.kawasaki.jp"),
			"city.kawasaki.jp",
		)

	def test_single_label_host(self):
		self.assertEqual(psl.registrable_domain("localhost"), "localhost")

	def test_unicode_suffix(self):
		self.assertEqual(psl.public_suffix("пример.рф"), "рф")
		self.assertEqual(psl.registrable_domain("пример.рф"), "пример.рф")
		self.assertEqual(psl.registrable_domain("shop.пример.рф"), "пример.рф")

	def test_trailing_dot_is_ignored(self):
		self.assertEqual(psl.registrable_domain("example.com."), "example.com")


if __name__ == "__main__":
	unittest.main()
