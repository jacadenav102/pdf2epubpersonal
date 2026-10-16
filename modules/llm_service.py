"""
A drop-in replacement for marker-pdf's ClaudeService that survives rate limits.

Selected via ``PdfConverter(llm_service="modules.llm_service.ResilientClaudeService")``.
It sends exactly the same system prompt / user content as marker's ClaudeService
(so output quality is unchanged) but adds:

* a process-wide rate limiter shared by marker's worker threads, honoring
  ``retry-after`` and pausing proactively using ``anthropic-ratelimit-*`` headers;
* retries with exponential backoff for 429/529/5xx/timeouts/connection errors;
* an on-disk response cache (checkpoint): re-running the same conversion reuses
  every successful answer and only re-sends the calls that failed;
* fail-fast on authentication errors and run-level statistics (see get_stats()).
* structured answers: the schema is sent as a forced tool call, so the API
  returns parsed JSON (marker's prompts show non-JSON examples and HTML inside
  JSON strings is often badly escaped); free-text answers are still accepted
  through a lenient parser, and an invalid answer is asked for once more
  (with a larger token budget if it was cut off).
"""
from __future__ import annotations

import json
import threading
from typing import Annotated, List

import anthropic
import PIL
from marker.logger import get_logger
from marker.schema.blocks import Block
from marker.services.claude import ClaudeService
from pydantic import BaseModel

from modules.llm_resilience import (
    FatalLLMError,
    LLMStats,
    RateLimiter,
    ResponseCache,
    cache_key,
    call_with_retries,
)
from modules.llm_parsing import lenient_parse, tool_for_schema, validate_object

logger = get_logger()

SERVICE_PATH = "modules.llm_service.ResilientClaudeService"
# Upper bound when retrying a truncated answer. Larger non-streaming requests
# are rejected by the Anthropic SDK (it requires streaming above ~21k tokens).
MAX_RETRY_TOKENS = 16384

_state_lock = threading.Lock()
_stats = LLMStats()
_limiter: RateLimiter | None = None
_fatal: FatalLLMError | None = None


def reset_state(requests_per_minute: float = 0) -> None:
    """Start a fresh run (called once per PDF)."""
    global _stats, _limiter, _fatal
    with _state_lock:
        _stats = LLMStats()
        _limiter = RateLimiter(rpm=requests_per_minute)
        _fatal = None


def get_stats() -> LLMStats:
    return _stats


def get_fatal_error() -> FatalLLMError | None:
    return _fatal


def _get_limiter(rpm: float) -> RateLimiter:
    global _limiter
    with _state_lock:
        if _limiter is None:
            _limiter = RateLimiter(rpm=rpm)
        return _limiter


class ResilientClaudeService(ClaudeService):
    # Overrides of marker's BaseService defaults (30 s / 2 retries / 3 s).
    timeout: Annotated[int, "Per-request timeout in seconds."] = 180
    max_retries: Annotated[int, "Retries per request (429/529/5xx/timeouts)."] = 8
    retry_wait_time: Annotated[int, "Base delay (s) for exponential backoff."] = 5
    llm_requests_per_minute: Annotated[float, "Hard cap on requests/minute (0 = adaptive only)."] = 0
    # Must be a non-None string: marker's verify_config_keys rejects None strings.
    llm_cache_dir: Annotated[str, "Directory for cached responses ('' disables caching)."] = ""
    claude_use_tools: Annotated[
        bool, "Ask for the answer as a forced tool call (structured JSON) instead of free text."
    ] = True
    invalid_response_retries: Annotated[int, "Extra attempts when an answer does not match the schema."] = 1

    def __init__(self, config=None):
        super().__init__(config)
        self._client = None
        self._client_lock = threading.Lock()
        self._cache = ResponseCache(self.llm_cache_dir or None)
        self._limiter = _get_limiter(self.llm_requests_per_minute)

    def get_client(self):
        # One shared client (connection pooling). SDK retries are disabled:
        # retries are handled by call_with_retries with a shared rate limiter.
        with self._client_lock:
            if self._client is None:
                self._client = anthropic.Anthropic(api_key=self.claude_api_key, max_retries=0)
            return self._client

    def _system_prompt(self, response_schema: type[BaseModel]) -> str:
        # Identical to marker.services.claude.ClaudeService.__call__.
        schema_example = response_schema.model_json_schema()
        return f"""
Follow the instructions given by the user prompt.  You must provide your response in JSON format matching this schema:

{json.dumps(schema_example, indent=2)}

Respond only with the JSON schema, nothing else.  Do not include ```json, ```,  or any other formatting.
""".strip()

    def __call__(
        self,
        prompt: str,
        image: PIL.Image.Image | List[PIL.Image.Image] | None,
        block: Block | None,
        response_schema: type[BaseModel],
        max_retries: int | None = None,
        timeout: int | None = None,
    ):
        global _fatal
        stats = get_stats()
        stats.add("requests")
        if _fatal is not None:
            raise _fatal  # e.g. invalid API key: do not keep hammering the API

        max_retries = self.max_retries if max_retries is None else max(max_retries, self.max_retries)
        timeout = self.timeout if timeout is None else max(timeout, self.timeout)

        system_prompt = self._system_prompt(response_schema)
        image_data = self.format_image_for_llm(image)
        messages = [{"role": "user", "content": [*image_data, {"type": "text", "text": prompt}]}]

        key = cache_key(
            model=self.claude_model_name,
            max_tokens=self.max_claude_tokens,
            system=system_prompt,
            prompt=prompt,
            images=[part["source"]["data"] for part in image_data],
        )
        cached = self._cache.get(key)
        if cached is not None:
            stats.add("cache_hits")
            return cached

        client = self.get_client()
        tool = tool_for_schema(response_schema) if self.claude_use_tools else None

        def send(max_tokens):
            kwargs = dict(
                system=system_prompt,
                model=self.claude_model_name,
                max_tokens=max_tokens,
                messages=messages,
                timeout=timeout,
            )
            if tool is not None:
                # Forced tool call: the API returns the answer as parsed JSON.
                kwargs.update(tools=[tool], tool_choice={"type": "tool", "name": tool["name"]})
            raw = client.messages.with_raw_response.create(**kwargs)
            return raw.parse(), raw.headers

        max_tokens = self.max_claude_tokens
        for attempt in range(self.invalid_response_retries + 1):
            try:
                response = call_with_retries(
                    lambda: send(max_tokens),
                    self._limiter,
                    stats,
                    max_retries=max_retries,
                    base_delay=self.retry_wait_time,
                    describe=response_schema.__name__,
                )
            except FatalLLMError as exc:
                with _state_lock:
                    _fatal = exc
                logger.error(f"Fatal LLM error, stopping LLM calls: {exc}")
                raise

            if response is None:
                return {}

            result = self._extract(response, response_schema, stats)
            if result:
                self._cache.put(
                    key, result, meta={"model": self.claude_model_name, "schema": response_schema.__name__}
                )
                return result

            reason = getattr(response, "stop_reason", "")
            if attempt < self.invalid_response_retries:
                stats.add("retries")
                if reason == "max_tokens":  # answer was cut off: allow a longer one
                    max_tokens = min(max_tokens * 2, MAX_RETRY_TOKENS)
                logger.info(f"Invalid {response_schema.__name__} response (stop_reason={reason}); asking again")

        stats.add("invalid_responses")
        logger.warning(f"Invalid {response_schema.__name__} response from Claude (stop_reason={reason})")
        return {}

    def _extract(self, response, response_schema: type[BaseModel], stats: LLMStats) -> dict | None:
        """Schema instance from a tool call, or (fallback) from the text answer."""
        texts = []
        for part in getattr(response, "content", None) or []:
            kind = getattr(part, "type", "")
            if kind == "tool_use":
                result = validate_object(getattr(part, "input", None), response_schema)
                if result:
                    return result
            elif kind == "text":
                texts.append(getattr(part, "text", "") or "")
        text = "".join(texts)
        if not text.strip():
            return None
        result = self.validate_response(text, response_schema)  # marker's strict parser
        if result:
            return result
        result = lenient_parse(text, response_schema)
        if result:
            stats.add("repaired")
        return result
