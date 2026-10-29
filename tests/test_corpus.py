"""Corpus, fuzz and performance tests.

These prove that no input can crash the check and that a normal link is
analysed quickly enough to feel instant.
"""

import contextlib
import os
import random
import time
import unittest

from _norlay_link_checker import (
	MAX_URL_CHARS,
	InvalidURL,
	NoURLFound,
	URLTooLong,
	analyze,
	render_report,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(PROJECT_ROOT, "tests", "corpus", "urls.txt")


def corpus_urls() -> list[str]:
	urls = []
	with open(CORPUS, encoding="utf-8") as handle:
		for line in handle:
			line = line.strip()
			if not line or line.startswith("#"):
				continue
			urls.append(line)
	return urls


class CorpusTests(unittest.TestCase):
	def test_corpus_is_not_empty(self):
		self.assertGreater(len(corpus_urls()), 40)

	def test_every_corpus_entry_is_handled(self):
		for url in corpus_urls():
			with self.subTest(url=url):
				try:
					analysis = analyze(url)
				except (NoURLFound, InvalidURL, URLTooLong):
					continue
				text = render_report(analysis)
				self.assertIn("Summary:", text)
				self.assertNotIn("\x00", text)


class FuzzTests(unittest.TestCase):
	ALPHABET = (
		"abcABC0123.:/?#@[]\\%_-~ =&+,;!()'\"<>"
		"\u202a\u202e\u200b\u200d\ufeff\u0430\u03b1\u4e2d\U0001f600\t\n"
	)

	def test_random_strings_never_raise(self):
		generator = random.Random(20261029)
		for _ in range(5000):
			length = generator.randrange(0, 80)
			text = "".join(generator.choice(self.ALPHABET) for _ in range(length))
			with self.subTest(text=text), contextlib.suppress(
				NoURLFound,
				InvalidURL,
				URLTooLong,
			):
				analyze(text)

	def test_long_random_strings_never_raise(self):
		generator = random.Random(7)
		for _ in range(50):
			length = generator.randrange(1000, MAX_URL_CHARS + 1)
			text = "".join(generator.choice(self.ALPHABET) for _ in range(length))
			with self.subTest(length=length), contextlib.suppress(
				NoURLFound,
				InvalidURL,
				URLTooLong,
			):
				analyze(text)

	def test_maximum_length_url(self):
		url = "https://example.com/" + "a" * (MAX_URL_CHARS - len("https://example.com/"))
		analysis = analyze(url)
		self.assertEqual(len(analysis.parsed.raw), MAX_URL_CHARS)

	def test_oversized_clipboard_text_is_truncated(self):
		text = "https://example.com/" + "a" * (MAX_URL_CHARS * 2)
		analysis = analyze(text)
		self.assertTrue(analysis.truncated)


class PerformanceTests(unittest.TestCase):
	def test_normal_link_is_fast(self):
		url = "https://login.example.co.uk/account/settings?session=12345"
		# Warm the lazily loaded data files first.
		analyze(url)
		start = time.perf_counter()
		for _ in range(50):
			analysis = analyze(url)
			render_report(analysis)
		elapsed = time.perf_counter() - start
		self.assertLess(elapsed / 50, 0.2)

	def test_long_link_is_fast(self):
		url = "https://sub.example.com/" + "segment/" * 500
		url = url[:MAX_URL_CHARS]
		analyze(url)
		start = time.perf_counter()
		for _ in range(10):
			analyze(url)
		elapsed = time.perf_counter() - start
		self.assertLess(elapsed / 10, 0.2)


if __name__ == "__main__":
	unittest.main()
