# Norlay Link Checker
# Copyright (C) 2026 Norlay
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

"""Ask Gemini to explain one address.

Only this module talks to the network.  It sends the address, a handful of
facts already worked out locally, and the fixed instruction from
:mod:`.prompt`.  No page is fetched, no history is kept and nothing is written
to disk.

The default model is chosen for free-tier economy: Gemini 3.5 Flash-Lite is
free, fast and does this narrow job well, while Gemini 3.8 Flash has a much
tighter daily free allowance.
"""

from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

from .errors import GeminiError
from .prompt import SYSTEM_PROMPT, build_user_text
from .sanitize import clean

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

USER_AGENT = "NorlayLinkChecker/1.1 (+https://norlay.fit/)"

#: Cheapest useful model: free tier, minimal thinking by default.
DEFAULT_MODEL = "gemini-3.5-flash-lite"

#: Offered in the settings dialog.  A free-text model name is also accepted.
MODEL_IDS = (
	"gemini-3.5-flash-lite",
	"gemini-3.8-flash",
	"gemini-3.6-flash",
)

#: Enough for 80 words with room to spare.  Output tokens are quota.
_MAX_OUTPUT_TOKENS = 320

#: Never read more than this from a response.
MAX_RESPONSE_BYTES = 262144

_RETRY_DELAY = re.compile(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"')
_BLOCKED_REASONS = {
	"SAFETY",
	"RECITATION",
	"BLOCKLIST",
	"PROHIBITED_CONTENT",
	"SPII",
	"IMAGE_SAFETY",
}


def _thinking_config(model: str) -> dict | None:
	"""Spend as few reasoning tokens as the model allows.

	The Flash-Lite models already default to minimal thinking, and sending an
	unsupported value is a 400, so the setting is only sent where it is known.
	"""
	if model.startswith(("gemini-3.8", "gemini-3.7", "gemini-3.6")):
		return {"thinkingLevel": "low"}
	return None


def build_payload(url: str, facts: list[str] | tuple[str, ...], model: str) -> dict:
	"""Build the JSON body for one ``generateContent`` call."""
	generation_config: dict = {
		"temperature": 0.2,
		"topP": 0.95,
		"maxOutputTokens": _MAX_OUTPUT_TOKENS,
	}
	thinking = _thinking_config(model)
	if thinking is not None:
		generation_config["thinkingConfig"] = thinking
	return {
		"systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
		"contents": [
			{"role": "user", "parts": [{"text": build_user_text(url, facts)}]},
		],
		"generationConfig": generation_config,
	}


def _default_transport(
	url: str,
	body: bytes,
	headers: dict[str, str],
	timeout: float,
) -> tuple[int, bytes]:
	request = urllib.request.Request(url, data=body, headers=headers, method="POST")
	try:
		with urllib.request.urlopen(request, timeout=timeout) as response:
			return response.status, response.read(MAX_RESPONSE_BYTES)
	except urllib.error.HTTPError as error:
		try:
			payload = error.read(MAX_RESPONSE_BYTES)
		except Exception:
			payload = b""
		return error.code, payload
	except (TimeoutError, socket.timeout) as error:
		raise GeminiError("timeout") from error
	except urllib.error.URLError as error:
		reason = getattr(error, "reason", None)
		if isinstance(reason, (TimeoutError, socket.timeout)):
			raise GeminiError("timeout") from error
		raise GeminiError("network") from error
	except OSError as error:
		raise GeminiError("network") from error


def _error_for_status(status: int, body: bytes) -> GeminiError:
	text = body.decode("utf-8", "replace")
	if status == 400:
		kind = "auth" if "api key" in text.lower() else "request"
		return GeminiError(kind)
	if status in (401, 403):
		return GeminiError("auth")
	if status == 404:
		return GeminiError("model")
	if status == 429:
		match = _RETRY_DELAY.search(text)
		detail = match.group(1) if match else ""
		return GeminiError("quota", detail)
	if status >= 500:
		return GeminiError("server")
	return GeminiError("response")


def parse_response(status: int, body: bytes) -> str:
	"""Return the reply text, or raise :class:`GeminiError`."""
	if status != 200:
		raise _error_for_status(status, body)

	try:
		data = json.loads(body.decode("utf-8"))
	except (UnicodeDecodeError, json.JSONDecodeError) as error:
		raise GeminiError("response") from error
	if not isinstance(data, dict):
		raise GeminiError("response")

	if isinstance(data.get("error"), dict):
		code = data["error"].get("code")
		if isinstance(code, int):
			raise _error_for_status(code, body)
		raise GeminiError("response")

	feedback = data.get("promptFeedback")
	if isinstance(feedback, dict) and feedback.get("blockReason"):
		raise GeminiError("blocked")

	candidates = data.get("candidates")
	if not isinstance(candidates, list) or not candidates:
		raise GeminiError("response")

	candidate = candidates[0] if isinstance(candidates[0], dict) else {}
	reason = candidate.get("finishReason")
	parts = (candidate.get("content") or {}).get("parts") or []
	chunks = [
		part.get("text", "")
		for part in parts
		if isinstance(part, dict) and not part.get("thought") and part.get("text")
	]
	text = "".join(chunks).strip()

	if not text:
		raise GeminiError("blocked" if reason in _BLOCKED_REASONS else "response")
	return text


def explain(
	url: str,
	facts: list[str] | tuple[str, ...] = (),
	api_key: str = "",
	model: str = DEFAULT_MODEL,
	timeout: float = 25.0,
	transport=None,
) -> str:
	"""Return a plain-text explanation of *url*.

	Raises :class:`GeminiError` for anything the user needs to act on.
	"""
	key = (api_key or "").strip()
	if not key or not url:
		raise GeminiError("config")

	chosen_model = (model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
	payload = build_payload(url, facts, chosen_model)
	body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
	endpoint = ENDPOINT.format(model=urllib.parse.quote(chosen_model, safe=""))
	headers = {
		"Content-Type": "application/json; charset=utf-8",
		"x-goog-api-key": key,
		"User-Agent": USER_AGENT,
	}

	send = transport or _default_transport
	status, response_body = send(endpoint, body, headers, timeout)
	text = clean(parse_response(status, response_body))
	if key in text:
		# Defensive: a model echoing the key must not put it in a window.
		text = text.replace(key, "[key]")
	return text
