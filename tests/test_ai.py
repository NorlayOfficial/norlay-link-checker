"""Tests for the Gemini client: payload, parsing, errors and quota economy."""

import json
import unittest

from _norlay_link_checker.ai import DEFAULT_MODEL, GeminiError, explain
from _norlay_link_checker.ai.gemini import (
	MAX_RESPONSE_BYTES,
	build_payload,
	parse_response,
)
from _norlay_link_checker.ai.prompt import SYSTEM_PROMPT, build_user_text, shorten_url
from _norlay_link_checker.ai.sanitize import clean


def success_body(text: str) -> bytes:
	return json.dumps(
		{"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]},
	).encode()


class PayloadTests(unittest.TestCase):
	def test_system_prompt_is_the_fixed_instruction(self):
		payload = build_payload("https://example.com/", [], DEFAULT_MODEL)
		self.assertEqual(payload["systemInstruction"]["parts"][0]["text"], SYSTEM_PROMPT)

	def test_output_is_capped_to_save_quota(self):
		payload = build_payload("https://example.com/", [], DEFAULT_MODEL)
		self.assertLessEqual(payload["generationConfig"]["maxOutputTokens"], 400)
		self.assertLessEqual(payload["generationConfig"]["temperature"], 0.5)

	def test_single_turn_no_history(self):
		payload = build_payload("https://example.com/", ["scheme=https"], DEFAULT_MODEL)
		self.assertEqual(len(payload["contents"]), 1)
		self.assertEqual(payload["contents"][0]["role"], "user")
		self.assertIn("https://example.com/", payload["contents"][0]["parts"][0]["text"])
		self.assertIn("scheme=https", payload["contents"][0]["parts"][0]["text"])

	def test_flash_lite_does_not_send_an_unknown_thinking_setting(self):
		payload = build_payload("https://example.com/", [], "gemini-3.5-flash-lite")
		self.assertNotIn("thinkingConfig", payload["generationConfig"])

	def test_flash_reduces_thinking_to_low(self):
		payload = build_payload("https://example.com/", [], "gemini-3.8-flash")
		self.assertEqual(payload["generationConfig"]["thinkingConfig"], {"thinkingLevel": "low"})

	def test_long_addresses_are_cut(self):
		url = "https://example.com/" + "a" * 5000
		text = build_user_text(url, [])
		self.assertIn("[truncated]", text)
		self.assertLess(len(text), 3000)

	def test_shorten_url_keeps_normal_links(self):
		url = "https://example.com/a?b=c"
		self.assertEqual(shorten_url(url), url)


class ParseTests(unittest.TestCase):
	def test_plain_answer(self):
		self.assertEqual(parse_response(200, success_body("A login page.")), "A login page.")

	def test_thought_parts_are_ignored(self):
		body = json.dumps(
			{
				"candidates": [
					{
						"content": {
							"parts": [
								{"text": "hidden reasoning", "thought": True},
								{"text": "Visible answer."},
							],
						},
					},
				],
			},
		).encode()
		self.assertEqual(parse_response(200, body), "Visible answer.")

	def test_blocked_prompt(self):
		body = json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}).encode()
		with self.assertRaises(GeminiError) as caught:
			parse_response(200, body)
		self.assertEqual(caught.exception.kind, "blocked")

	def test_empty_candidate(self):
		with self.assertRaises(GeminiError) as caught:
			parse_response(200, json.dumps({"candidates": []}).encode())
		self.assertEqual(caught.exception.kind, "response")

	def test_bad_json(self):
		with self.assertRaises(GeminiError) as caught:
			parse_response(200, b"<html>nope</html>")
		self.assertEqual(caught.exception.kind, "response")

	def test_status_mapping(self):
		cases = {
			400: "request",
			401: "auth",
			403: "auth",
			404: "model",
			429: "quota",
			500: "server",
			503: "server",
			418: "response",
		}
		for status, kind in cases.items():
			with self.subTest(status=status):
				with self.assertRaises(GeminiError) as caught:
					parse_response(status, b"{}")
				self.assertEqual(caught.exception.kind, kind)

	def test_retry_delay_is_kept_for_the_message(self):
		body = b'{"error": {"code": 429, "details": [{"retryDelay": "37s"}]}}'
		with self.assertRaises(GeminiError) as caught:
			parse_response(429, body)
		self.assertEqual(caught.exception.kind, "quota")
		self.assertEqual(caught.exception.detail, "37")

	def test_error_object_in_a_200(self):
		body = b'{"error": {"code": 403, "message": "bad key"}}'
		with self.assertRaises(GeminiError) as caught:
			parse_response(200, body)
		self.assertEqual(caught.exception.kind, "auth")


class SanitiseTests(unittest.TestCase):
	def test_markdown_is_removed(self):
		raw = "## Title\n\n**example.com** is a `test` site.\n\n- first\n- second"
		cleaned = clean(raw)
		self.assertNotIn("##", cleaned)
		self.assertNotIn("**", cleaned)
		self.assertNotIn("`", cleaned)
		self.assertNotIn("- ", cleaned)
		self.assertIn("example.com", cleaned)

	def test_code_fences_are_removed(self):
		self.assertEqual(clean("```\nhello\n```"), "hello")

	def test_very_long_replies_are_cut(self):
		cleaned = clean("word " * 2000)
		self.assertLessEqual(len(cleaned), 1501)
		self.assertTrue(cleaned.endswith("…"))


class ExplainTests(unittest.TestCase):
	def test_missing_key_is_a_config_error(self):
		with self.assertRaises(GeminiError) as caught:
			explain("https://example.com/", [], "", DEFAULT_MODEL)
		self.assertEqual(caught.exception.kind, "config")

	def test_request_goes_to_the_chosen_model(self):
		seen = {}

		def transport(url, body, headers, timeout):
			seen["url"] = url
			seen["body"] = json.loads(body)
			seen["headers"] = headers
			seen["timeout"] = timeout
			return 200, success_body("Looks like a shop.")

		answer = explain(
			"https://shop.example/item",
			["scheme=https"],
			"secret-key",
			"gemini-3.5-flash-lite",
			timeout=12,
			transport=transport,
		)
		self.assertEqual(answer, "Looks like a shop.")
		self.assertIn("gemini-3.5-flash-lite:generateContent", seen["url"])
		self.assertEqual(seen["headers"]["x-goog-api-key"], "secret-key")
		self.assertEqual(seen["timeout"], 12)
		self.assertIn("shop.example", seen["body"]["contents"][0]["parts"][0]["text"])

	def test_the_key_never_appears_in_the_answer(self):
		def transport(url, body, headers, timeout):
			return 200, success_body("Your key secret-key is fine.")

		answer = explain("https://example.com/", [], "secret-key", transport=transport)
		self.assertNotIn("secret-key", answer)

	def test_response_read_is_bounded(self):
		self.assertLessEqual(MAX_RESPONSE_BYTES, 512 * 1024)


if __name__ == "__main__":
	unittest.main()
